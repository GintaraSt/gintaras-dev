+++
title = "Concurrent vs Parallel vs Asynchronous"
date = "2023-06-13T20:42:39+03:00"
author = ""
authorTwitter = "" #do not include @
cover = ""
tags = ["", ""]
keywords = ["", ""]
description = ""
showFullContent = false
readingTime = false
hideComments = false
color = "" #color from the theme settings
+++

Some time ago I wanted to better understand how asynchronous code works in C#. It seemed that it should’ve been some simple 5 minutes google search, however, quite quickly I got myself into a deep rabbit hole about the differences between parallel, concurrent and asynchronous processing.

In this blog post I will try to summarize what I found and what I think I understood about these three types of processing.

I will cover the following in this post:
1. [Synchronous vs Parallel vs Concurrent](#Synchronous-vs-Parallel-vs-Concurrent)
   1. [Examples](#Examples)
      1. Synchronous execution
      2. Parallel execution
      3. Concurrent execution
   2. Wrap up
2. Asynchronous execution
   1. Examples
      1. Async by nature task - executed synchronously
      2. Async by nature task - executed asynchronously
      3. Asynchronous vs Parallel and Concurrent
   2. How does our program know when the asynchronous task completed?
   3. What happens when I await async method immediately after calling it?
3. Summary

# Synchronous vs Parallel vs Concurrent
Defining difference between parallel and concurrent is quite easy and you probably already heard about it.

- Parallel - processing multiple tasks at the same time.
- Concurrent - having multiple tasks in progress at the same time.

Basically parallel computing is when you ask your computer to perform multiple tasks at at the same time in parallel and it actually is doing all that work at the same time.

Concurrent is when you tell your computer to perform multiple tasks and it performs them in pieces. Starting one, jumping to another, then returning to the previous one and so on. This is made possible by what’s called “Context Switching” (more on that later).
## Examples

It is much easier to understand the difference with actual examples, so lets go through some and see how synchronous vs parallel vs concurrent behave.

Lets take the following code:
```C#
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
### Synchronous execution

Lets simply call the method 4 times passing different values as id argument for each call:

```csharp
DoWork(1);
DoWork(2);
DoWork(3);
DoWork(4);
```

This is a simple example of synchronous execution. Each method will run to completion before executing the next one. The results of this code is as follows (truncated seconds fraction a bit for readability):

```powershell
Starting 1: 17:08:50.316
Completed 1 - 17:08:56.639
Starting 2: 17:08:56.639
Completed 2 - 17:09:02.990
Starting 3: 17:09:02.990
Completed 3 - 17:09:09.308
Starting 4: 17:09:09.308
Completed 4 - 17:09:15.538

Time took: 25222ms, 252225803ticks
```

As you can see each run took about 6 seconds to complete on my machine. I also added a Stopwatch to track exact time it took for all 4 methods to complete. As you can see, when running synchronously, all four calls completed in ~25 seconds.

In this case the execution would look something like this: