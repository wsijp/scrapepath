
Scrapepath
----------

[Scrapepath](https://github.com/wsijp/scrapepath) is a templated web scraping syntax. [Scrapepath is pip installable](https://pypi.org/project/scrapepath/) via `pip install scrapepath`.


Requirements
------------

Install the required Python dependencies using the provided requirements.txt file, by:

```bash
pip install -r requirements.txt
```


Usage
-----

To run an example, execute on the command line without arguments:

```bash
./parser
```

To use within Python:

```python
from parser import NodeParser

np = NodeParser(soup_template, soup, live_url)
np.hop_template()
print (json.dumps(np.result_dict, indent = 2, default = str))
```

Where `soup_template` is a `BeautifulSoup` of the template file, `soup` is a `BeautifulSoup` of the scraped page and `live_url` the url of the scraped page.

Templates
---------

HTML pages are scraped using HTML templates, consisting of a mixture of the most important tags, and statements.

Templates consist of HTML files containing nested tags leading to the scraping element of interest.

The parser is based on `BeautifulSoup`.

Example 1: Scraping data
-----------------------

The following examples are from scraped pages `examples/example1a.html` and template `examples/scraped1.html`. Run the example using:

`./parser.py examples/example1a.html examples/scraped1.html`

This scrapes the target page `scraped1.html` using the `template example1a.html`. The text item "Tea" is scraped from the target page using the `record` attribute in the template page. A path to the target text ("Tea") is specified in the template using tags that correspond to the target page. So, to scrape from:

```html

<ul class = "my_list">
  <li class = "my_item">Coffee</li>
  <li class = "my_item"><span class = "cuppa">Tea</span></li>
  <li class = "my_item">Milk</li>
</ul>

```

Use template:

```html
<ul class = "my_list">
  <span class = "cuppa" record = "text as favorite"></span>
</ul>

```

This yields a dictionary containing the scraped data under the key "favorite" as specified in the `record` attribute:

```json
{
  "favorite": "Tea"
}
```
The `text` statement within the record attribute corresponds to a function that obtains text from inside the HTML tag, and `favorite` is the key to record the data against. The `text` function can be replaced with custom Python functions.

 Starting from the outer node, `<ul>` , in the template, the parser looks for the first node in the scraped page that matches the template node in type and attributes. In this case, matching a ul with a ul, and class my_list with class my_list. Then, the same search takes place using the template node children, now confined within the children of the scraped node. So nested template nodes represent paths. The `<li>` node is not included in the template, as it would point the search to the first element of the list.

 In this case, nesting the template nodes is needlessly specific. There are no other nodes of class "cuppa", so we can omit the `<ul>` and `<li>` items, and the following template will record the same data:

 ```html
 <span class = "cuppa" record = "text as favorite"></span>

 ```

So paths along many nested nodes in the scraped page can be summarized by only a few nodes that define a unique path to the scraped data.


Loops:

A `for` loop scrapes all items in the list. In this simple example, we record only one variable (item_text) per item:

Template:

```html
    <ul class = "my_list">
      <for items = "items" condition = "i < 5">
        <li class ="my_item" record = "text as item_text">
        </li>
      </for>
    </ul>
```

This results in the output:

```json
{
  "items": [
    {
      "item_text": "Coffee"
    },
    {
      "item_text": "Tea"
    },
    {
      "item_text": "Milk"
    },
    {
      "item_text": "Biscuits"
    },
    {
      "item_text": "Chocolate"
    }
  ]
}
```

Here, the parser matches all the children of the `<for>` template node to the children of the `<ul>` node in the scraped page `scraped1.html` . Run the example using: `./parser.py examples/example1b.html examples/scraped1.html`. The `condition` node indicates that only the first 5 items should be recorded, where `i` is the loop counter variable.

Example 2: for loops on mixed nodes
----------------------------------

In the following html, a `<for>` template loop node needs to enclose two template nodes, one for each tag (div and p) and class (my_item and milk_class):

To scrape from:

```html
<div class = "my_list">
  <div class = "my_item">Coffee</div>
  <div class = "my_item"><span class = "cuppa">Tea</span></div>
  <p class = "milk_class">Milk</p>
  <div class = "my_item">Biscuits</div>
  Chocolate
</div>
```

Use template:

```html
<div class = "my_list">
  <for items = "items" >
    <div class ="my_item" record = "text as item_text"></div>
    <p class ="milk_class" record = "text as item_text"></p>
  </for>
</div>

```

However, the `<for>` template loop node is unable to record the text element "chocolate", as the `<for>` only looks for proper nodes among the children of the `<div class = "my_list">` node. To do this, a `<forchild>` template loop node is needed, along with a `<str>` template node to record the `NavigableString` element "chocolate":

Template:

```html

<div class = "my_list">
  <forchild items = "items_with_string" >
    <div class ="my_item" record = "text as item_text"></div>
    <p class ="milk_class" record = "text as item_text"></p>
    <str record = "text as item_text"></div>
  </forchild>
</div>

```

In this case, the parser looks for the first match to the first template node (the child of the `<for>` node), and loops over its sibblings, probing with all template nodes (the children of this for node). Run this example using `examples/example1b.html` and `examples/scraped1.html`.

Example 3: Jumping to linked pages
---------------------------------

Follow links on pages using the `<jump>` template node:

To scrape from:

```html

<a href="example_linked.html"></a>

```

Use template:

```html
    <a record = "href as my_link">
      <jump on = "my_link">
        <ibody>
          <div class = "message" record = "text as msg_from_link"></div>
        </ibody>
      </jump>
    <a>
```

Here, the nodes within the `<jump>` node act on the linked page.

This example is invoked with:

```bash
./parser.py examples/example3a.html examples/scraped3.html
```
