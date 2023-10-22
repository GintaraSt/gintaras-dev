+++
title = "JsonPathConvert - a system to help with deeply nested json structures"
date = "2023-10-17T05:55:41+03:00"
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
   '/images/json-path/thumbnail.png',
   '/images/json-path/Carousel-0.png',
   '/images/json-path/Carousel-1.png',
   '/images/json-path/Carousel-2.png',
   '/images/json-path/Carousel-3.png',
   '/images/json-path/Carousel-4.png',
   '/images/json-path/Carousel-5.png'
]
copyright = false
+++

Recently I've been working on a small Newtonsoft's Json.NET package decorator 'JsonPathConvert'. This decorator is designed to help solving issue where you might want to deserialize json from some deeply nested json into a simple flat POCO without replicating the entire nested structure.

The tool I created might not yet be production ready, however, I think the concept is quite interesting to share, and continue developing.

I will cover the following in this post:
- [The issue I am trying to address](#the-issue-i-am-trying-to-address)
- [JsonPath Attribute and JsonPathConvert](#jsonpath-attribute-and-jsonpathconvert)
  - [What does it do](#what-does-it-do)
  - [How does it work](#how-does-it-work)
  - [Limitations and plans](#limitations-and-plans)
  - [Performance (not great)](#performance-not-great)
- [Wrap up](#wrap-up)

# The issue I am trying to address

While working with 3rd party APIs I often find myself parsing deep data structures just to get a couple of values.
This usually involves ether manually mapping values from `JObject` into my custom class or creating nested classes structure to get some values buried deep inside the json.

To illustrate the issue - lets take Bitbucket Cloud API's [List a pull request activity log](https://developer.atlassian.com/cloud/bitbucket/rest/api-group-pullrequests/#api-repositories-workspace-repo-slug-pullrequests-pull-request-id-activity-get) endpoint. This endpoint can return quite a deep structure.

Lets take a sample response where pull request activity log includes a single update (pull request was opened, merged or declined), and for now lets imagine it returns that update alone, not an entire array of objects.

The JSON of such response would look as follows (copied straight from bitbucket [documentation](https://developer.atlassian.com/cloud/bitbucket/rest/api-group-pullrequests/#api-repositories-workspace-repo-slug-pullrequests-pull-request-id-activity-get), however, I removed a lot of parts that are irrelevant for this example):
```json
{
   "update": {
       "state": "OPEN",
       "author": {
           "display_name": "Name Lastname",
           "links": {
               "self": {
                   "href": "https://api.bitbucket.org/2.0/users/%7B%7D"
               },
           },
           "account_id": ""
       },
   },
   "pull_request": {
       "title": "username/NONE: small change from onFocus to onClick to handle tabbing through the page and not expand the editor unless a click event triggers it",
       "id": 5695
   }
}
```
Lets say we need to get the following values:
- Pull request id `pull_request > id`
- Pull request title `pull_request > title`
- State `update > state`
- Author name `update > author > display_name`
- Author account id `update > author > account_id`
- Author self link `update > author > links > self > href`

Presented with task like this I would immediatelly consider 2 options:
1. Create a class replicating json structure
2. Create a flat class and parse each value using JObject 

The first option would result in the following structure to get the fields we need:
```csharp
public record PullRequestAction(
   PullRequestUpdate Update,
   [JsonProperty("pull_request")] PullRequest PullRequest);

public record PullRequest(string Title, int Id);

public record PullRequestUpdate(
   string State,
   PullRequestAuthor Author);

public record PullRequestAuthor(
   [JsonProperty("display_name")] string Name,
   [JsonProperty("account_id")] string AccountId,
   BitbucketAuthorLinks Links);

public record BitbucketAuthorLinks(BitbucketLink Self);

public record BitbucketLink(string Href);
```
Then we could simply parse the json using NewtonsoftJson as follows:
```csharp
var res = JsonConvert.DeserializeObject<PullRequestAction>(json);
```

In most cases, this approach would be preferable as it is quite clean, and the structure we get closely matches the one we are deserializing. Because of this - it would also be trivial to get back the original json structure when serializing.

However, often we may not want to write deep structure just to get some specific value buried somewhere deep inside the json. In these cases we can use the second approach - parsing using JObject. For this we could create a following structure:
```csharp
public record PullRequestAction(
   string State,
   string AuthorName,
   string AuthorAccountId,
   string AuthorSelfHref,
   string PullRequestTitle,
   int PullRequestId);
```
Then we could parse each value using JObject as follows:
```csharp
var jObject = JObject.Parse(json);
var res = new PullRequestAction(
   State: jObject["update"]["state"].ToObject<string>(),
   AuthorName: jObject["update"]["author"]["display_name"].ToObject<string>(),
   AuthorAccountId: jObject["update"]["author"]["account_id"].ToObject<string>(),
   AuthorSelfHref: jObject["update"]["author"]["links"]["self"]["href"].ToObject<string>(),
   PullRequestTitle: jObject["pull_request"]["title"].ToObject<string>(),
   PullRequestId: jObject["pull_request"]["id"].ToObject<int>());
```
This would give us flat object with all the values. However the parsing part is quite tedious to write. Also, even though we need the entire Author object - we still write out assignment of each field.

While this gives us simpler object - serializing this back to a deep nested structure can be a bit challenging.

There are ways of mixing these two approaches together to atleast not have to write out each Author property, however, for now we are considering a simple example.

# JsonPath Attribute and JsonPathConvert

As a possible solution for this problem I created a small tool that wraps NewtonsoftJson, and adds `JsonPath` attribute. The idea of this attribute is to make it easy to change the way objects are serialized and deserialized.

The tool is available as a [nuget package JsonPathConvert](https://www.nuget.org/packages/jsonpathconvert/), and can be installed using .NET CLI `dotnet add package jsonpathconvert --version 1.0.1`.

The source code is available in my github [GintarasDev > JsonPath](https://github.com/GintarasDev/JsonPath). Any contributions to this package are welcome, and appreciated.

## What does it do
Lets say we have the following structure with attributes:
```csharp
public record PullRequestAction(
   [JsonPath("update.")] string State,
   [JsonPath("update.author")] PullRequestAuthor Author,
   [JsonPath("pull_request.title")] string PullRequestTitle,
   [JsonPath("pull_request.id")] int PullRequestId);

public record PullRequestAuthor(
    [JsonProperty("display_name")] string Name,
    [JsonProperty("account_id")] string AccountId,
    [JsonPath("links.self.href")] string SelfHref);
```
Now we can deserialize this object from json in a similar way as if we actually replicated the json structure:
```csharp
var res = JsonPathConvert.DeserializeObject<PullRequestAction>(json);
```
This also works other way arround. Once the `JsonPath` attributes are added - you can also serialize flat object into a nested json structure as follows:
```csharp
var json = JsonPathConvert.SerializeObject<PullRequestAction>(pullRequestAction);
```
The result will be identical to the starting value:
```json
{
   "update": {
       "state": "OPEN",
       "author": {
           "display_name": "Name Lastname",
           "links": {
               "self": {
                   "href": "https://api.bitbucket.org/2.0/users/%7B%7D"
               },
           },
           "account_id": ""
       },
   },
   "pull_request": {
       "title": "username/NONE: small change from onFocus to onClick to handle tabbing through the page and not expand the editor unless a click event triggers it",
       "id": 5695
   }
}
```

The JsonPath attribute takes a string representing the path you want a value to be serialized to, and deserialized from. In this path '.' (dot character) represents nesting.

So in the above example path `update.author` - means that `Author` property will be deserialized using value of `author` found in `update` object. 
Similarly, when serializing, the `Author` - value will be placed in `update` object with a name of `author`. So this works both ways.

In the Author property example - the property itself is an another class which contains `JsonPath` in its properties. In this case property `SelfHref` in `PullRequestAuthor` class will be serialized to a value stored in `update` > `author` > `links` > `self` > `href`.
If you were to serialize `PullRequestAuthor` on its own, the value of `SelfHref` would be placed in `links` > `self` > `href`.
What I am trying to say is that `JsonPathConvert` decorator will correctly handle nested classes.

Due to the nature of this attribute `JsonProperty` attribute is no longer necessary as `JsonPath` attribute can control the name by itself. Using this attribute without any dots (eg. `[JsonPath("MyNewName")]`) should function identically to `JsonProperty` attribute.

Additionally, you can use `JsonPath` attribute with dot at the end. In this case the actual name of the property will be used as the ending of the path. So in the example above where we write state property as `[JsonPath("update.")] string State,` - the actual path used will be `update.state`.

Another thing worth mentioning is that `JsonPathConvert` class includes 'TypesToIgnore' property. This property is a list of values which will not be scanned for `JsonPath` properties. It is usefull for stuff like `DateTime` where Newtonsoft's `JsonConvert` would just serialize it to date-time string, so we don't want to scan it's insides. Types ignored by default are:
* DateTime
* DateTime?
* DateTimeOffset
* DateTimeOffset?
* Guid
* Guid?
* TimeSpan
* TimeSpan?
* string
* decimal
* decimal?

## How does it work

The way `JsonPathConvert` class works under the hood is quite simple conceptually, although implementation itself got a bit complex (nd will probably get even more complex once I start optimizing things).

Basically, once you call `JsonPathConvert.SerializeObject` - the SerializeObject method performs following actions:
1. Recursively scans object properties, and their inner properties, and so on, searching for properties with `JsonPath` attribute. Then generates key-value pairs with current and desired path for each property.
2. Converts the object we want to serialize into a json dictionary where each key has the current path to the property in the class structure, and each value is the value of that property.
3. Updates keys using path modification key-value pairs gotten in the step 1.
4. Generates new nested dictionaries strucure where key is 1 part of the path, and value is ether the value of the property, or another dictionary with the next part of the path.
5. Serializes the nested dictionary structure into json.

Lets consider the previous example where `PullRequestAction` contains `Author` with `SelHref` property. The flow for this property would look as follows:

After scanning the object recursivelly we would get key-value pair with current path being set to `Author.SelfHref` and the desired path being set to `update.author.links.self.href`.

Then, the object would be converted to dictionary with a key-value pair where key is `Author.SelfHref`, and the value matches the one stored in `PullRequestAuthor` `SelfHref` property.

After that the keys in the dictionary would be updated using path modification key-value pairs from step one. That means that our key-value pair in objects dictionary would be changed from `Author.SelfHref` to `update.author.links.self.href`.

Once all of that is done, a new dictionary would be created where each part of the path would be nested into another. Lets say the value of `SelfHref` is 'https://http.cat/', then the generated dictionaries structure would look something like this:
```csharp
new Dictionary<string, object>()
{
    ["update"] = new Dictionary<string, object>()
    {
        ["author"] = new Dictionary<string, object>()
        {
            ["links"] = new Dictionary<string, object>()
            {
                ["self"] = new Dictionary<string, object>()
                {
                    ["href"] = "https://http.cat/"
                }
            }
            // Other properties
        }
    }
    // Other properties
}
```

Finally we can simply call Newtonsoft's `JsonConvert.SerializeObject` and pass our generated dictionary to it. The resulting output will be correctly nested structure.

Deserialization works in basically the same way:
1. Get paths to modify key-value pairs, then swap keys and values in places.
2. Create json dictionary from json.
3. Update paths in this dictionary using path modification key-value pairs. Remember that they are swapped so instead of actual path in object being updated to the one in JsonPath attribute - the one in JsonPath attribute will be updated to the actual path in our object.
4. Generate nested dictionaries structure.
5. Deserialize generated nested dictionaries structure.
   
So we are basically reusing the same methods.

## Limitations and plans

At the time of writting, this package is a bit limited:
* It only supports public properties (no fields support).
* '.' is used as path separator so your json key cannot have it in the name.
* If your class structure contains Dictionary with non-primite key, JsonPathConvert will not be able to work with that.

I am planning to update it a bit in the following months:
* Add fields support.
* Optimizations.
* Add intelisense (will probably write a separe blog about this):
  * To warn about invalid paths formats.
  * To warn about not supported non-primitive dictionary keys.
* Implement way to exclude all classes in specific namespace and its subnamespaces.

## Performance (not great)

This package is quite slow at the moment. It might be ok for light use in non performance sensitive API, but in general I would suggest waiting for performance oriented updates if performance is a concern.

Benchmanr results are presented below.
```
BenchmarkDotNet v0.13.9+228a464e8be6c580ad9408e98f18813f6407fb5a, Windows 11 (10.0.22621.2428/22H2/2022Update/SunValley2)
AMD Ryzen 7 2700X, 1 CPU, 16 logical and 8 physical cores
.NET SDK 7.0.100
  [Host]     : .NET 7.0.0 (7.0.22.51805), X64 RyuJIT AVX2
  DefaultJob : .NET 7.0.0 (7.0.22.51805), X64 RyuJIT AVX2

```
| Method                            | Mean       | Error     | StdDev    | Ratio | RatioSD |
|-----------------------------------|-----------:|----------:|----------:|------:|--------:|
| Baseline (Newtonsoft JsonConvert) |   8.619 μs | 0.1086 μs | 0.0963 μs |  1.00 |    0.00 |
| Serialize                         | 217.035 μs | 1.3642 μs | 1.2094 μs | 25.18 |    0.29 |
| Serialize (WithoutCustomPaths)    |   8.625 μs | 0.1079 μs | 0.0901 μs |  1.00 |    0.02 |

As you can see, when passing type that contains `JsonPath` attributes - the serialization is 25.18 times slower.

The main performance eating parts are generation of flattened json dictionary from object (~36 μs) and generation of nested dictionaries structure (~97 μs).
I am planning to update and improve the performance of this system in the future, but for now, you decide how much that matters to you (it probably should matter at least a bit).

# Wrap up

In my very subjective opinion this tool is quite useful. However, it requires a bit of work to make it a bit faster.
Also, if you're considering using it - please keep in mind that it might still have some bugs.

The repository is public, and you're more than welcome to help develop this tool further.

Additional thing to consider when using tool like this is clean code. I suspect quite a bit of self discipline might be needed to not fall into a hell with classes full of custom paths that do not resemble json they are deserialized from and serialized to at all. In my opinion this tool solves quite specific problem, and should be used sparingly. In many cases you should prefer replicating json structure. This tool is best when you need to get few specific properties from large, deeply nested json, and should probably not be used if you are deserializing the entire object anyways.