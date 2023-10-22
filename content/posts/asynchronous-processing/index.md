+++
title = "Asynchronous processing"
date = "2023-06-17T21:37:14+03:00"
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
   '/images/asynchronous-processing/thumbnail.png',
   '/images/asynchronous-processing/Carousel-0.png',
   '/images/asynchronous-processing/Carousel-1.png',
   '/images/asynchronous-processing/Carousel-2.png',
   '/images/asynchronous-processing/Carousel-3.png',
   '/images/asynchronous-processing/Carousel-4.png',
   '/images/asynchronous-processing/Carousel-5.png'
]
copyright = false
+++

> This is a continuation of post [Concurrent vs Parallel processing]( {{< relref "concurrent-vs-parallel-vs-asynchronous-processing" >}}). I strongly suggest reading that one first as this post relies on some context and terminology defined there.

In this post I will try to summarize what I found out, and _what I think I understood_ about the asynchronous execution. What type of tasks can be performed asynchronously, and what it means to perform task asynchronously compared to paraller, and concurrent execution.

I will cover the following in this post:
- [Asynchronous tasks](#asynchronous-tasks)
  - [Synchronous execution](#synchronous-execution)
  - [Asynchronous execution](#asynchronous-execution)
  - [Asynchronous vs Parallel and Concurrent](#asynchronous-vs-parallel-and-concurrent)
  - [How does our program know that asynchronous part completed?](#how-does-our-program-know-that-asynchronous-part-completed)
  - [What happens when we await asynchronous method immediately after calling it?](#what-happens-when-we-await-asynchronous-method-immediately-after-calling-it)
- [Wrap up](#wrap-up)

All examples used in this post can be found in [this github repo](https://github.com/GintarasDev/blogpost-parallel-concurrent-async).

# Asynchronous tasks

I separated asynchronous to a separate post for a reason. Although it is sometimes mixed with concurrent and parallel - it is actually quite different from them. And the difference comes from the tasks that are being performed as you can't just take any task and perform it asynchronously.

Tasks I used in examples of [Concurrent vs Parallel processing]( {{< relref "concurrent-vs-parallel-vs-asynchronous-processing" >}}) post were CPU bound. That means that CPU has to work to complete them. However, some tasks we want our processor to do may require sending some work to other parts of our system (or other systems entirely), and then waiting to get the results back to continue.

As an example - saving a file will require our processor to take the data from Cache or RAM and pass it to some permanent storage device (eg. SSD). Once the data is passed to our storage device, our processor needs to wait for that device to write it, and then pass next part or confirm successful saving.

> When processor needs to wait for some other part of our, or other system, to complete doing something before it can continue - the task is asynchronous by nature.

Any task involving waiting for some other part of our, or other system, is asynchronous by nature. Writing/reading data to/from disk, sending HTTP requests where we wait for some other server to respond or even getting data from other program running on the same machine - in many cases can be done asynchronously.

Performing task asynchronously means that we are allowing our processor to work on other things while the asynchronous part, being performed by some other part of the system, is completed.

To better understand this, lets do some comparisons.

To test asynchronous code we want some task that would be asynchronous by nature.

One of the most obvious choices would be to write something to disk. However, for testing purposes, I found it to be a bit too unreliable as disk write speeds can vary drastically and I couldn’t find a good way to achieve stable speeds where multiple runs would consistently complete in similar times.

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
<sup>_We could use `Task.Delay` dirrectly instead of wrapping it in some API, however, I thought an example with API requests would be more realistic, and relatable than random `Task.Delay` calls._</sup>

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

Synchronously calling the test method 4 times will cause each call to be executed one by one, and the total execution time to reach ~20 seconds.

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

We call this method similarly as if we were executing it synchronously, however, we then take Tasks returned by these methods, and wait for their completion later in a similar way as we did with parallel and concurrent examples in [Concurrent vs Parallel processing]( {{< relref "concurrent-vs-parallel-vs-asynchronous-processing" >}}) post (as all of these use the same C# `System.Threading.Tasks` library).

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
    <strong>Note:</strong> we are still using only 1 physical thread.
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

The code, for both parallel and concurrent execution, is the same as previously. So parallel execution can be performed using the following code:

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

This gives us the following results for parallel execution:

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

The results with parallel execution looks very similar to asynchronous execution. However, that’s only because we are running this test on a machine with 16 physical threads. To see the difference, and the issue with using parallel execution for async tasks, we just need to scale the number of tasks we are performing to exceed the number of physical threads we have (basically, we want to reach enough tasks for them to be executed in parallel and concurrently at the same time).

For that, lets put the method call in a loop:

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

This is because when executing this task in parallel - each thread is sending the request and waiting for the response. When executing asynchronously - the request is sent, the virtual thread is paused, and only resumed once it gets the response. It is free to do anything else while the asynchronous part of the task is being waited for.

If you are more of a visual person, this difference can be quite easily explained with some diagrams.

Concurrent execution of multiple asynchronous by nature tasks would look something like this:

![Resize](/images/concurrent-vs-parallel-vs-asynchronous/concurrent-async.png?width=1000px)

Here, I used orange-ish color to mark parts of the tasks that require actual CPU work, and dark red-ish - parts where CPU just has to wait for something to be done by some other part of our system. I put each concurrent task into a separate line to represent virtual thread that is working on it when it gets CPU time. Above the start of each task I put the full length task for reference of how long the task will take since it was started.

This diagram only shows 1 physical thread with multiple virtual threads, but using multiple physical threads will look very similar as long as your virtual/physical threads ratio is greater than 1 (you have more tasks than physical threads to execute them).

The issue may not immediately be apparent, but once you see the asynchronous execution diagram it is much clearer:

![Resize](/images/concurrent-vs-parallel-vs-asynchronous/asynchronous-async.png?width=1000px)

When executing asynchronously - no thread is actually waiting for the task to be completed. Hence, our program can just perform the synchronous part of the task and continue to execute other things until `await` is called. (In the examples above we were executing some CPU bound work while we were waiting for responses to our requests).

In concurrent execution on the other hand - our physical threads were actually going through each virtual thread we spun for our requests methods and just waiting. It was still better than synchronous execution as time passes even if our CPU is not actively waiting for it to pass, so if we take any individual task - our CPU was waiting less for response on that specific task than it would when executing it synchronously, but still, majority of execution time was spent waiting.

Asynchronous execution just gets rid of the waiting part all together as our CPU can just prepare the task and return to it once there’s something it can actually do.

You may also have noticed that all of this was done on 1 thread in async diagram. Our program will not spin new threads for each async task. It will just execute the method call up to the point where the actual asynchronous part begins, and then return to execute other code (in our case next method call) until the point where we await for the results of the asynchronous task.

Once we sent all the requests and called `await` - our virtual thread will be paused and our physical thread will switch to work on other things until responses to our requests start comming in.

Once our program will be notified about the completion of asynchronous part of the task - our task will be taken by any available physical thread, its context will be loaded, and it will continue like nothing happened from the part where it started waiting.

## How does our program know that asynchronous part completed?

This question alone requires a dedicated blog post to answer. Thankfully someone else already written it.

“There Is No Thread” article by Stephen Cleary explains it quite well. I myself do not fully understand it, hence, I will not even try to write a TLDR of it, but I would strongly encourage you to read it: https://blog.stephencleary.com/2013/11/there-is-no-thread.html

## What happens when we await asynchronous method immediately after calling it?

This was one of the first questions I thought of that caused me to dive deep into the rabbit hole of asynchronous, parallel and concurrent execution differences.

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
- Virtual thread that was executing our request is paused, and our CPU continues to work on other things.

At this point, our physical thread is free to take other HTTP requests to work on.

Once the delay time passes:
- Virtual thread is resumed on any free physical thread.
- Remaining part of the request is executed (in this case we return the empty response to the request).

The benefit of using `async` `await` in such way is that our API can handle much more requests than it could if we were to use parallel/concurrent execution that would synchronously wait for the delay to complete.

# Wrap up

The differences between parallel and concurrent execution may not be that important as these are quite similar concepts that complement each other, however, asynchronous execution is quite a different concept that should not be confused with the other two.

The main reason I choose this topic to write about was due to how much vague and sometimes contradicting information there is about parallel, concurrent, and asynchronous execution. The differences between these concepts can often be confusing, and not obvious.

You may not need information provided in this post in day to day work, however, knowing how things actually work, especially things that are supposed to be fundamental, can really help when reasoning about code.

I hope this post, together with [Concurrent vs Parallel processing]( {{< relref "concurrent-vs-parallel-vs-asynchronous-processing" >}}) - helped to clear up some confusion between these three.