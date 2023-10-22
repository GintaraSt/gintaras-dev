+++
title = "Concurrent vs Parallel processing"
date = "2023-06-13T20:42:39+03:00"
author = ""
authorTwitter = "" #do not include @
cover = ""
tags = ["", ""]
keywords = ["", ""]
description = ""
toc = false
readingTime = false
hideComments = false
color = "" #color from the theme settings
carousel = true
pinned = true
images = [
   '/images/concurrent-vs-parallel-vs-asynchronous/thumbnail.png',
   '/images/concurrent-vs-parallel-vs-asynchronous/Carousel-0.png',
   '/images/concurrent-vs-parallel-vs-asynchronous/Carousel-1.png',
   '/images/concurrent-vs-parallel-vs-asynchronous/Carousel-2.png',
   '/images/concurrent-vs-parallel-vs-asynchronous/Carousel-3.png',
   '/images/concurrent-vs-parallel-vs-asynchronous/Carousel-4.png',
   '/images/concurrent-vs-parallel-vs-asynchronous/Carousel-5.png'
]
copyright = false
+++

Some time ago I wanted to better understand how asynchronous code works in C#. It seemed that it should’ve been some simple 5 minutes google search, however, quite quickly I got myself into a deep rabbit hole about the differences between parallel, concurrent and asynchronous execution.

In this blog post I will try to summarize what I found and _what I think I understood_ about the differences concurrent, and parallel execution. Asynchronous execution will be disscussed in a continuation of this post [Asynchronous processing]( {{< relref "asynchronous-processing" >}}).

I will cover the following in this post:
- [Physical threads vs Virtual threads](#physical-threads-vs-virtual-threads)
- [Parallel vs Concurrent](#parallel-vs-concurrent)
  - [Synchronous execution](#synchronous-execution)
  - [Parallel execution](#parallel-execution)
  - [Concurrent execution](#concurrent-execution)
- [Wrap up](#wrap-up)

All examples used in this post can be found in [this github repo](https://github.com/GintarasDev/blogpost-parallel-concurrent-async).

# Physical threads vs Virtual threads
> In this article I often use terms "Physical thread" and "Virtual thread", it is important to understand the difference between these two to understand the differences between differenct execution types.
> 
> When you buy a CPU you will usually see Cores and Threads count in it's specifications. Eg. 8 Cores 16 Threads. In this article I will refer to these threads as `physical threads`, even though "Logical processors" would probably be more correct term (at least that's how Windows Task Manager calls them). [As an example, here's specification of Ryzen 7 2700X](https://www.amd.com/en/support/cpu/amd-ryzen-processors/amd-ryzen-7-desktop-processors/amd-ryzen-7-2700x)
> 
> ![Resize](/images/concurrent-vs-parallel-vs-asynchronous/ryzen-7-2700x-specs.png?width=500px)
> 
> No matter how many cores and physical threads your CPU supports - your operating system can create thousands of threads. In this article I will refer to these threads as `virtual threads`. As an example here's a screenshot of my Task Manager. My system is running the previously mentioned Ryzen 7 2700X with 16 physical threads (Shown as "Logical processors" in the screenshot), yet, it has almost 4k of virtual threads (Shown as "Threads" in the screenshot).
>
> ![Resize](/images/concurrent-vs-parallel-vs-asynchronous/ryzen-7-2700x-task-manager.png?width=500px)
> 
> The main difference is that:
> - Physical threads allow execution of multiple tasks in parallel.
> - Virtual threads allow to "pretend" that our processor can executed more tasks in parallel than it actually can.
>
> You may also wonder what a CPU Core is in this context, this is not very relevant to this article, but in short: Core is supposed to process 1 thread at the time, but, due to some magic technology called simultaneous multithreading (SMT), or as Intel calls it - "Hyper-Threading", it can efficiently allow 2 threads to share its resources and access caches and execution engine at the same time. Hence you almost always see modern CPUs with n cores and 2n threads (which I refer to as "physical threads" in this article).
>

# Parallel vs Concurrent
Defining difference between parallel and concurrent is quite easy and you probably already heard about it.

- Parallel - **processing** multiple tasks at the same time.
- Concurrent - having multiple tasks **in progress** at the same time.

Parallel execution is when you ask your computer to perform multiple tasks at the same time in parallel and it is working on all of those tasks at the same time.

Concurrent execution is when you tell your computer to perform multiple tasks and it performs them in pieces. Starting one, jumping to another, then returning to the previous one and so on. Basically, your CPU is only working on 1 task at a time and switches between tasks by using what’s called “Context Switching” (more on that later).

It is much easier to understand the difference with actual examples, so lets go through some and see how synchronous, parallel and concurrent execution differs.

Lets take the following code:
```csharp
   void DoWork(int id)
   {
      Console.WriteLine($"Starting {id}: {DateTime.UtcNow.TimeOfDay}");
      var sum = 0;
      for (var i = 1; i <= 10; i++)
         for (var j = 0; j <= 100_000_000; j++)
            sum += j / i;
         
      Console.WriteLine($"Completed {id} - {DateTime.UtcNow.TimeOfDay}");
   }
```
This method prints to console the time it started working, then loops through some numbers and perform some basic arithmetic's on them and once everything is done - it will print its completion time.

Each print statement includes id so we would know which of the methods printed it.

## Synchronous execution

At first, lets call our test method 4 times passing different values as id argument for each call:

```csharp
   DoWork(1);
   DoWork(2);
   DoWork(3);
   DoWork(4);
```

This is a simple example of synchronous execution. Each method will run to completion before executing the next one. The results of this code is as follows (seconds fraction was truncated a bit for readability):

```
   Starting 1:    17:08:50.316
   Completed 1 -  17:08:56.639
   Starting 2:    17:08:56.639
   Completed 2 -  17:09:02.990
   Starting 3:    17:09:02.990
   Completed 3 -  17:09:09.308
   Starting 4:    17:09:09.308
   Completed 4 -  17:09:15.538

   Time took: 25222ms, 252225803ticks
```

As you can see each run took about 6 seconds to complete on my machine. I also added a Stopwatch to track exact time it took for all 4 methods to complete. When running synchronously, all four calls completed in ~25 seconds.

Nothing special here, in this case the execution could be visualised as follows:
![Resize](/images/concurrent-vs-parallel-vs-asynchronous/synchronous-cpu-bound.png?width=800px)

Here, we only have 1 thread performing all the work.

## Parallel execution

Now lets update our code to run the method in parallel.

For that we can use `Task.Run` method which takes action we want to perform as an input, schedules it to run on a thread pool and then returns a `Task` to track its progress. We then use these returned tasks to await for all work to complete.

```csharp
   var parallelTask0 = Task.Run(() => DoWork(1));
   var parallelTask1 = Task.Run(() => DoWork(2));
   var parallelTask2 = Task.Run(() => DoWork(3));
   var parallelTask3 = Task.Run(() => DoWork(4));

   await Task.WhenAll(parallelTask0, parallelTask1, parallelTask2, parallelTask3);
```

This tells our program to schedule `DoWork` method to run on a thread pool 4 times, and then wait for all executions to complete. If our computer has enough free physical threads (in my case it has) - these methods will be executed in parallel (this is a bit simplified).

Executing this code provides results similar to these ones:

```
   Starting 1:    17:09:15.542
   Starting 2:    17:09:15.542
   Starting 3:    17:09:15.542
   Starting 4:    17:09:15.542
   Completed 4 -  17:09:22.522
   Completed 2 -  17:09:22.578
   Completed 3 -  17:09:22.592
   Completed 1 -  17:09:22.609

   Time took: 7071ms, 70717788ticks
```

There are few things you may notice:
- This time all methods started execution at roughly the same time.
- All methods completed at roughly the same time and at non-deterministic order. Running the code multiple times will result in completion order changing as each thread may perform slightly differently.
- All 4 methods were executed in ~7 seconds. This is because parallel execution actually runs all 4 methods at the same time on different physical threads.

You may notice that even though we used 4 threads instead of 1 - execution time only improved ~3.5 times instead of 4 times you may expect. This is because there is some overhead when scheduling and starting threads. The more work each physical thread has to execute - the less important this overhead will be.

If we would want to visualize parallel execution with diagram it would look something like this:

![Resize](/images/concurrent-vs-parallel-vs-asynchronous/parallel-cpu-bound.png?width=400px)

Each physical thread is executing a task, all working at the same time, allowing all tasks to be executed together, hence, decreasing time we need to wait for all tasks to complete.

## Concurrent execution
Running the same methods concurrently without parallelization is not as simple as it may seem. Concurrency allows us to pretend that our processor can do more things in parallel than it actually can.

In C#, using the same code as we used in parallel execution example may cause work to be done concurrently if our system does not have enough free physical threads to give for each of the tasks we want to execute.

We can take the same code as in parallel execution example and tell our operating system to only allow 1 physical thread to be used by our program. This will force it to not properly parallelize our tasks. The same effect could be achieved by simply starting more tasks than physical threads supported by our processor, but limiting number of physical cores from our code will ensure the code would still behave in a similar maner if ran on a system with different number of physical cores.
The updated code looks like this:

```csharp
   // Bind program to specific physical thread
   Process proc = Process.GetCurrentProcess();
   long affinityMask = 0x0001;
   proc.ProcessorAffinity = (IntPtr)affinityMask;

   // Run the test
   var concurrentTask0 = Task.Run(() => DoWork(1));
   var concurrentTask1 = Task.Run(() => DoWork(2));
   var concurrentTask2 = Task.Run(() => DoWork(3));
   var concurrentTask3 = Task.Run(() => DoWork(4));
```

<div class="note">
    <strong>Note:</strong> Processor affinity is windows specific API so this test will not work on other operating systems.
</div>

Running this code gives us the following output:

```
   Starting 4:    17:09:22.612
   Starting 1:    17:09:22.643
   Starting 2:    17:09:22.644
   Starting 3:    17:09:22.676
   Completed 4 -  17:09:46.998
   Completed 1 -  17:09:47.046
   Completed 2 -  17:09:47.096
   Completed 3 -  17:09:47.079

   Time took: 24485ms, 244850125ticks
```

The result might seem similar to the one we got when using parallel computing with multiple cores as each task was started at the same time and completed at roughly the same time in non-deterministic order. However, the execution time is back to being ~25 seconds, similar to the one we saw when executing code synchronously.

This is because concurrent execution does not actually execute all the methods at the same time. Instead it executes a bit of first one, then a bit of second one, then a bit of third one, then a bit of fourth one, a bit of first one again and so on…

This is achieved using something called "Context Switching". Context Switching is like pausing a task our physical thread is working on and saving its state. This allows our physical thread to work on other things, and then come back to the original task like it never stopped working on it.

Context Switching will take some time, so having too many virtual threads can cause performance to decrease because a lot of time will be spent while switching between tasks. In practice I found that unless you create thousands of virtual threads - that performance impact will not be very severe.

The concurrent execution on a single physical thread would look something like this:

![Resize](/images/concurrent-vs-parallel-vs-asynchronous/concurrent-cpu-bound.png?width=800px)

Here each number presents id that was passed to the method and each color represents a diferent virtual thread.
Each task is executed on a different virtual thread, however, these threads are sharing the time of single physical thread (CPU0). Our physical thread is giving a fraction of it's time to each of the virtual threads, so they could all do some work.

# Wrap up

Hopefully now you'll have a good understanding of what is the difference between parallel, and concurrent execution. Now if we reiterate the descriptions from the start of this article - they should be clearer:

- Parallel - **processing** multiple tasks at the same time.
- Concurrent - having multiple tasks **in progress** at the same time. Those tasks are not being worked on at the same time, they are just started one by one and being worked on sequentially, small parts at the time, giving the illusion of more things being done at the same time.

<div class="note">
    <strong>Note:</strong> In practice parallel and concurrent computing goes toe to toe. Modern PCs have multiple physical threads meaning they can perform multiple tasks at the time, and your PC always has much more virtual threads than physical ones. Most of the time when writting code you don't need to think about how many physical threads CPU running it will have.
</div>

While parallel, and concurrent execution are quite similar concepts that complement each other - asynchronous execution is quite a bit different context, and I would encourage you to read the [Asynchronous processing]( {{< relref "asynchronous-processing" >}}) post to found out how it differs, and why is it so important.