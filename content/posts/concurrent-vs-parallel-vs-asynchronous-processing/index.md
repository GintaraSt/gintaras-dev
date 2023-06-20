+++
title = "Concurrent vs Parallel vs Asynchronous processing"
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

In this blog post I will try to summarize what I found and **what I think I understood** about the differences between these.

I will cover the following in this post:
- [Physical threads vs Virtual threads](#physical-threads-vs-virtual-threads)
- [Parallel vs Concurrent](#parallel-vs-concurrent)
  - [Synchronous execution](#synchronous-execution)
  - [Parallel execution](#parallel-execution)
  - [Concurrent execution](#concurrent-execution)
  - [Parallel vs Concurrent Wrap up](#parallel-vs-concurrent-wrap-up)
- [Asynchronous tasks](#asynchronous-tasks)
  - [Synchronous execution](#synchronous-execution-1)
  - [Asynchronous execution](#asynchronous-execution)
  - [Asynchronous vs Parallel and Concurrent](#asynchronous-vs-parallel-and-concurrent)
  - [How does our program know that asynchronous part completed?](#how-does-our-program-know-that-asynchronous-part-completed)
  - [What happens when we await asynchronous method immediately after calling it?](#what-happens-when-we-await-asynchronous-method-immediately-after-calling-it)
- [Wrap up](#wrap-up)

All examples used in this post can be found in [this github repo](https://github.com/GintaraSt/blogpost-parallel-concurrent-async).

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

Basically parallel computing is when you ask your computer to perform multiple tasks at the same time in parallel and it actually is doing all that work at the same time.

Concurrent is when you tell your computer to perform multiple tasks and it performs them in pieces. Starting one, jumping to another, then returning to the previous one and so on. Basically, your CPU is only working on 1 task at a time and switches between tasks by using what’s called “Context Switching” (more on that later).

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

At first, lets simply call our test method 4 times passing different values as id argument for each call:

```csharp
   DoWork(1);
   DoWork(2);
   DoWork(3);
   DoWork(4);
```

This is a simple example of synchronous execution. Each method will run to completion before executing the next one. The results of this code is as follows, seconds fraction was truncated a bit for readability:

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

For that we can simply use `Task.Run` method which takes action we want to perform as an input, schedules it to run on a thread pool and then returns a `Task` to track its progress. We then use these returned tasks to await for all work to complete.

```csharp
   var parallelTask0 = Task.Run(() => DoWork(1));
   var parallelTask1 = Task.Run(() => DoWork(2));
   var parallelTask2 = Task.Run(() => DoWork(3));
   var parallelTask3 = Task.Run(() => DoWork(4));

   await Task.WhenAll(parallelTask0, parallelTask1, parallelTask2, parallelTask3);
```

This basically tells our program to schedule `DoWork` method to run on a thread pool 4 times, and then wait for all executions to complete. If our computer has enough free physical threads (in my case it has) - these methods will be executed in parallel (this is a bit simplified).

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
Running the same methods concurrently without parallelization is not as simple as it may seem. Concurrency basically allows us to pretend that your processor can do more things at the same time than it actually can.

In C# using the same code as we used in parallel execution example may cause work to be done concurrently if your system does not have enough free physical threads to give for each of the tasks we want to execute.

So we will simply take the same code as in parallel execution example and tell our operating system to only allow 1 physical thread to be used by our program. Basically forcing it to not properly parallelize our tasks. The same effect could be achieved by simply starting more tasks than physical threads supported by our processor.
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
Context Switching will take some time, so having too many virtual threads can cause performance decrease just because a lot of time will be spent just switching between them. In practice I found that unless you create thousands of virtual threads - that performance impact will not be very severe.

The concurrent execution on a single physical thread would look something like this:

![Resize](/images/concurrent-vs-parallel-vs-asynchronous/concurrent-cpu-bound.png?width=800px)

Here each number presents id that was passed to the method and each color represents a diferent virtual thread.
Each task is executed on a different virtual thread, however, these threads are sharing the time of single physical thread (CPU0). Basically, our physical thread is giving a fraction of it's time to each of the threads, so they could all do some work.

## Parallel vs Concurrent Wrap up

Hopefully now you'll have a good understanding of what is the difference between parallel and concurrent execution. Now if we reiterate the descriptions from the start of this article - they should be clearer:

- Parallel - **processing** multiple tasks at the same time.
- Concurrent - having multiple tasks **in progress** at the same time. Those tasks are not being worked on at the same time, they are just started one by one and being worked on sequentially small parts at the time, giving the illusion of more things being done at the same time.

<div class="note">
    <strong>Note:</strong> In practice parallel and concurrent computing goes toe to toe. Modern PCs have multiple physical threads meaning they can perform multiple tasks at the time, and your PC always has much more virtual threads than physical ones. Most of the time when writting code you don't need to think about how many physical threads CPU running it will have.
</div>

# Asynchronous tasks

I separated asynchronous execution from the rest for a reason. Although it is sometimes mixed with concurrent and parallel - it is actually quite different from them. And the difference comes from the tasks that are being performed as you can't just take any task and perform it asynchronously.

Tasks I used in examples above are CPU bound. Meaning that CPU has to work to complete them. However, some tasks we want our processor to do may require sending some work to other parts of our system (or other systems entirely), and then waiting to get the results back to continue.

As an example - saving a file will require our processor to take the data from Cache or RAM and pass it to some permanent storage device (eg. SSD). Once the data is passed to our storage device, our processor needs to wait for the device to write it and then pass next part or confirm successful saving.

<div class="note">
    <strong>Note:</strong> When processor needs to wait for some other part of our, or other system, to complete doing something before it can continue - the task is asynchronous by nature.
</div>

Any task involving waiting for some other part of our, or other system, is asynchronous by nature. Writing/reading data to/from disk, sending HTTP requests where we wait for some other server to respond or even getting data from other program running on the same machine - in many cases can be done asynchronously.

Performing task asynchronously basically means that we are allowing our processor to work on other things while the asynchronous part, being performed by other part of the system, is completed.

To better understand this, lets do some comparisons again.

To test asynchronous code we want some task that would be asynchronous by nature.

One of the most obvious choices would be to simply write something to disk. However, for testing purposes, I found it to be a bit too unreliable as disk write speeds can vary drastically and I couldn’t find a good way to achieve stable speeds where multiple runs would consistently complete in similar times.

So what I decided to use instead was HTTP requests. For that I created a very simple API using .NET Minimal APIs, that provides a get endpoint “slow-response” that will send empty response 5 seconds after receiving the request.

```csharp
   var builder = WebApplication.CreateBuilder(args);
   var app = builder.Build();

   app.MapGet("/slow-response", async () =>
   {
      await Task.Delay(5_000); // Wait for 5 seconds before returning.
      return "";
   });

   app.Run();
```
<sup>*Yes, I am using asynchronous method `Task.Delay` while explaining asynchronous execution*</sup>

Using this for our investigation of asynchronous execution allows us to easily and reliably test asynchronous http client methods. Also, performing http requests are one of the most commonly met asynchronous task (well at least if you are a web developer), so it should be somewhat representetive of "real-world" (*whatever that means*) scenarios.

To be able to test Asynchronous vs Synchronous execution we can just start this API and forget about it for now.

## Synchronous execution

To call the example endpoint we can use C#’s built-in http client. Just like previously - we will wrap this call into a method and add some logging to notify when the method was called and when it completed it’s work:

```csharp
   static void SendRequest(int id)
   {
      Console.WriteLine($"Starting {id}: {DateTime.UtcNow.TimeOfDay}");
      
      var httpClient = new HttpClient();
      httpClient.Send(new HttpRequestMessage(HttpMethod.Get, "http://localhost:5201/slow-response"));
      
      Console.WriteLine($"Completed {id} - {DateTime.UtcNow.TimeOfDay}");
   }
```

This method can be called synchronously as any other method:

```csharp
   SendRequest(0);
   SendRequest(1);
   SendRequest(2);
   SendRequest(3);
```

The result of this way of calling our endpoints is as follows:

```
   Starting 0:    13:02:56.614
   Completed 0 -  13:03:01.732
   Starting 1:    13:03:01.733
   Completed 1 -  13:03:06.749
   Starting 2:    13:03:06.749
   Completed 2 -  13:03:11.766
   Starting 3:    13:03:11.766
   Completed 3 -  13:03:16.768

   Time took: 20158ms, 201581867ticks
```

Synchronously calling the test method 4 times will cause each call to be executed one by one and the total execution time to reach ~20 seconds.

## Asynchronous execution

To call the same endpoint asynchronously we need to update it a bit as follows:

```csharp
   static async Task SendRequestAsync(int id)
   {
      Console.WriteLine($"Starting {id}: {DateTime.UtcNow.TimeOfDay}");
      
      var httpClient = new HttpClient();
      await httpClient.SendAsync(new HttpRequestMessage(HttpMethod.Get, "http://localhost:5201/slow-response"));
      
      Console.WriteLine($"Completed {id} - {DateTime.UtcNow.TimeOfDay}");
   } 
```

All we did here was replacing http clients `Send` with `SendAsync`, and changing method signature to `async Task`.

We call this method similarly as if we were executing it synchronously, however, we then take Task and await for it returns and wait for its completion later in a similar way as we did with parallel and concurrent examples (as all of these use the same C# `System.Threading.Tasks` library).

```csharp
   var asyncTask0 = SendRequestAsync(0);
   var asyncTask1 = SendRequestAsync(1);
   var asyncTask2 = SendRequestAsync(2);
   var asyncTask3 = SendRequestAsync(3);

   await Task.WhenAll(asyncTask0, asyncTask1, asyncTask2, asyncTask3);
```

The result of this will be similar to the following:

```
   Starting 0:    18:41:40.750
   Starting 1:    18:41:40.843
   Starting 2:    18:41:40.844
   Starting 3:    18:41:40.844
   Completed 3 -  18:41:45.877
   Completed 1 -  18:41:45.877
   Completed 2 -  18:41:45.877
   Completed 0 -  18:41:45.877

   Time took: 5142ms, 51422785ticks
```

As you can see from this example, the async code took only 5 seconds to complete all four requests instead of 20 seconds it took when running these requests synchronously.

Just to prove that this is indeed running asynchronously and not simply in parallel with dedicated thread for each task, we can do the same thing we did when testing concurrent code and limit our program from using more than 1 physical thread by setting processor affinity (binding our program to 1 specific physical thread):

```csharp
   Process proc = Process.GetCurrentProcess();
   long affinityMask = 0x0001;
   proc.ProcessorAffinity = (IntPtr)affinityMask;
```

Setting this before running the test does not change results in any meaningful way:

```
   Starting 0:    18:46:13.400
   Starting 1:    18:46:13.476
   Starting 2:    18:46:13.476
   Starting 3:    18:46:13.476
   Completed 0 -  18:46:18.512
   Completed 2 -  18:46:18.512
   Completed 1 -  18:46:18.512
   Completed 3 -  18:46:18.512

   Time took: 5117ms, 51177010ticks
```

When we used the same technique while testing concurrency with CPU heavy task - we saw that even though tasks were all being executed “at the same time”, they took similar amount of time to complete as when executed synchronously. This time however, the execution doesn’t really care that there’s only 1 physical thread as the majority of work our asynchronous tasks are doing do not require our CPU to do anything until response from our API comes. 

As we have all this time while waiting - we can execute some CPU heavy work while asynchronous tasks are being executed:

```csharp
   Process proc = Process.GetCurrentProcess();
   long affinityMask = 0x0001;
   proc.ProcessorAffinity = (IntPtr)affinityMask;

   var asyncTask0 = SendRequestAsync(0);
   var asyncTask1 = SendRequestAsync(1);
   var asyncTask2 = SendRequestAsync(2);
   var asyncTask3 = SendRequestAsync(3);
   // Execute some CPU bound work
   DoWork(4);

   await Task.WhenAll(asyncTask0, asyncTask1, asyncTask2, asyncTask3);
```
<div class="note">
    <strong>Note:</strong> Note that we are still using only 1 physical thread.
</div>

Running this code gives the following output:

```
   Starting 0:    18:51:07.669
   Starting 1:    18:51:07.806
   Starting 2:    18:51:07.807
   Starting 3:    18:51:07.80
   Starting 4:    18:51:07.807
   Completed 2 -  18:51:12.903
   Completed 1 -  18:51:12.903
   Completed 3 -  18:51:12.903
   Completed 0 -  18:51:12.903
   Completed 4 -  18:51:14.478

   Time took: 6812ms, 68128064ticks
```

Notice that our asynchronous tasks still took the same 5 seconds to complete, and `DoWork` method took 6 seconds just as before, meaning it was executing while async tasks were "running".

## Asynchronous vs Parallel and Concurrent

To better convey the advantages of asynchronous execution, lets compare it against executing the non-async version of our method using parallel and concurrent execution.

The code for both parallel and concurrent execution are basically the same as previously. So parallel execution can be performed using the following code:

```csharp
   // Parallel
   var parallelTask0 = Task.Run(() => SendRequest(0));
   var parallelTask1 = Task.Run(() => SendRequest(1));
   var parallelTask2 = Task.Run(() => SendRequest(2));
   var parallelTask3 = Task.Run(() => SendRequest(3));
   // Execute some CPU bound work
   DoWork(4);

   await Task.WhenAll(parallelTask0, parallelTask1, parallelTask2, parallelTask3);
```

The above code gives us the following results for parallel execution:

```
   Starting 4:    19:01:20.304
   Starting 1:    19:01:20.306
   Starting 2:    19:01:20.306
   Starting 0:    19:01:20.306
   Starting 3:    19:01:20.306
   Completed 1 -  19:01:25.434
   Completed 3 -  19:01:25.434
   Completed 2 -  19:01:25.434
   Completed 0 -  19:01:25.434
   Completed 4 -  19:01:26.679

   Time took: 6378ms, 63789771ticks
```

The results with parallel execution looks basically identical to asynchronous execution. However, that’s only because I am running this test on a machine with 16 physical threads. To see the difference and the issue with using parallel execution for async tasks we just need to scale the number of tasks we are performing to exceed the number of our physical threads we have (basically, we want to reach enough tasks for them to be executed in parallel and concurrently at the same time).

For that, lets simply put the method call in a loop:

```csharp
   var parallelTasks = new List<Task>();
   for (int i = 0; i < 64; i++)
   {
         RunInParallel(i);
   }
   DoWork(65);

   await Task.WhenAll(parallelTasks);

   void RunInParallel(int id) => parallelTasks.Add(Task.Run(() => SendRequest(id)));
```
<div class="note">
    <strong>Note:</strong> We could achieve similar results by binding our program to single physical thread again, however, that way we would only demonstrate concurrent processing execution times.
</div>

<div class="note">
    <strong>Note:</strong> We are using `RunInParallel` method to wrap the actual adding of the tasks to the list due to the way lambda expressions work in loops (as it is not triggered immediately, it will not take the value of `i` immediately).
</div>
</br>

This gives us the following result (I removed most of it as it’s quite long):

```
   Starting 5:    19:15:04.896
   Starting 2:    19:15:04.896
   Starting 0:    19:15:04.896
   Starting 65:   19:15:04.893
   Starting 3:    19:15:04.896
   ...
   Starting 63:   19:15:06.540
   Completed 65 - 19:15:11.241
   Completed 23 - 19:15:11.656
   Completed 34 - 19:15:11.656
   Completed 56 - 19:15:11.656
   Completed 19 - 19:15:11.656
   ...
   Completed 26 - 19:15:21.688

   Time took: 16801ms, 168012948ticks
```

When running 64 asynchronous by nature tasks in parallel (and 1 task that does actual CPU bound work) - it took us ~16 seconds to complete all of them.

Now lets do the same using asynchronous execution:

```csharp
   sw = Stopwatch.StartNew();

   var asynchronousTasks = new List<Task>();
   for (int i = 0; i < 64; i++)
   {
         asynchronousTasks.Add(SendRequestAsync(i));
   }
   DoWork(65);

   await Task.WhenAll(asynchronousTasks);
```

And the result of this code:

```
   Starting 0:    19:29:19.384
   Starting 1:    19:29:19.628
   Starting 2:    19:29:19.629
   Starting 3:    19:29:19.629
   Starting 4:    19:29:19.629
   ...
   Starting 65:   19:29:19.634
   Completed 47 - 19:29:24.689
   Completed 28 - 19:29:24.689
   Completed 49 - 19:29:24.689
   Completed 40 - 19:29:24.689
   Completed 53 - 19:29:24.689
   ...
   Completed 65 - 19:29:25.978

   Time took: 6598ms, 65983510ticks
```

Even though we had more tasks than we have physical threads - we still managed to execute all tasks in roughly the same time of ~5 seconds for sending requests and ~6 seconds for CPU bound task.

Actually, this execution time doesn’t really change even if we change the for loop to execute **1000** asynchronous requests. While if we change parallel example to send even 200 requests - it will complete all of them in ~67 seconds.

This is because when executing this task in parallel - each thread is actually waiting for task to complete. When executing asynchronously - the task is started and thread will only continue it once it got the response. It is free to do anything else while the asynchronous part of the task is being waited for.

If you are more of a visual person, this difference can be quite easily explained with some diagrams.

Concurrent execution of multiple asynchronous by nature tasks would look something like this:

![Resize](/images/concurrent-vs-parallel-vs-asynchronous/concurrent-async.png?width=1000px)

Here, I used yellow-ish to mark parts of the tasks that require actual CPU work, and blue-ish - parts where CPU just has to wait. I put each concurrent task into a separate line to represent virtual thread that is working on it when it gets CPU time. Above the start of each task I put the full length task for reference of how long the task will take since it was started.

This diagram only shows 1 physical thread with multiple virtual threads, but using multiple physical threads will look basically the same if your virtual/physical threads ratio is greater than 1.

The issue may not immediately be apparent, but once you see the asynchronous execution diagram it is much clearer:

![Resize](/images/concurrent-vs-parallel-vs-asynchronous/asynchronous-async.png?width=1000px)

When executing asynchronously - no thread is actually waiting for the task to be completed. Hence, our program can just perform the synchronous part of the task and continue to execute other things until `await` is called. (In the examples above we were executing some CPU bound work while we were waiting for responses to our requests).

In concurrent execution on the other hand - our physical threads were actually going through each virtual thread we spun for our requests methods and just waiting. It was still better than synchronous execution as time passes even if our CPU is not actively waiting for it to pass, so if we take any individual task - our CPU was waiting less for response on that specific task than it would when executing it synchronously, but still, majority of execution time was spent waiting.

Asynchronous execution basically just gets rid of the waiting part all together as our CPU can just prepare the task and return to it once there’s something it can actually do.

You may also have noticed that all of this was done on 1 thread in async diagram. Our program will not spin new threads for each async task. It will just execute the method call up to the point where the actual asynchronous part begins, and then return to execute other code (in our case next method call) until the point where we await for the results of the asynchronous task.

Once we sent all the requests and called `await` - our virtual thread will be paused and our physical thread will switch to work on other things until responses to our requests start comming in.

Once our program will be notified about the completion of asynchronous part of the task - our task will be taken by any available physical thread, its context will be loaded, and it will continue like nothing happened from the part where it started waiting.

## How does our program know that asynchronous part completed?

This is actually a quite complicated topic which I won’t dive into as it is quite long and complicated (and this post is getting quite long already). I spent quite a lot of time trying to understand it, but it is quite complicated and more hardware/OS related, so I wouldn't be confident writing about that.

“There Is No Thread” article by Stephen Cleary explains it very well, but I do not yet understand it enough to just be able to take any asynchronous task and uderstand how it works: https://blog.stephencleary.com/2013/11/there-is-no-thread.html

## What happens when we await asynchronous method immediately after calling it?

This was one of the first questions I thought of that caused me to dive deep into the rabbit hole of asynchronous, parallel and concurrent differences.

Lets take previously shown .NET minimal API code that we used to test asynchronous tasks:

```csharp
   app.MapGet("/slow-response", async () =>
   {
      await Task.Delay(5_000); // Wait for 5 seconds before returning.
      return "";
   });
```

Here we are calling `Task.Delay` and awaiting for it immediately. What is happening here is:
- Request is received.
- Synchronous part of `Task.Delay` is executed.
- Virtual thread that was executing our request is paused and our CPU continues to work on other things.

At this point, our physical thread is free to take other HTTP requests to work on.

Once the delay time passes:
- Virtual thread is resumed on any free physical thread.
- Remaining part of the request is executed (in this case we return the empty response to the request).

The benefit of using `async` `await` in such way is that our API can handle much more requests than it could if we were to use parallel/concurrent execution that would synchronously wait for the delay to complete.

# Wrap up
The differences between parallel and concurrent execution may not be that important as these are quite similar concepts that complement each other, however, asynchronous execution is quite a different concept that should not be confused with the other two.

The main reason I choose this topic to write about was due to how much vague and sometimes contradicting information there is about the differences between these and how they work. Especially about asynchronous execution. The inconsistent terminology and slighly different meaning of word "Thread" in different contexts definatelly doesn't help to understand this.

I hope this helped to clear up some confusion between these three.