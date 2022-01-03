---
title: "Dies ist eine deutsche Testseite"
date: 2020-04-18T10:07:21+06:00
# post image
image: "images/blog/post-1.jpg"
# post type (regular/featured)
type: "featured"
# meta description
description: "Dies ist die Metabeschreibung"
# post draft
draft: false
---


#### Exemplarische Überschrift

Hier ist ein Beispiel für eine Überschrift. Sie können diese Überschrift verwenden, indem Sie den Markdownify-Regeln folgen. Zum Beispiel: Verwenden Sie `#` für Überschrift 1 und `######` für Überschrift 6.

# Überschrift 1 
<br>

## Überschrift 2 

<br>

### Überschrift 3 

<br>

#### Überschrift 4 

<br>

##### Überschrift 5 

<br>

###### Überschrift 6


<hr>

##### Hervorhebung

Hervorhebung, auch kursiv genannt, mit *Asterisken* oder _Unterstrichen_.

Starke Betonung, auch fett, mit **Asterisken** oder __Unterstrichen__.

Kombinierte Hervorhebung mit **Rasterzeichen und _Unterstrichen_**.

Durchstreichen verwendet zwei Tilden. ~~Durchstreichen~~.

<hr>

##### Link
[Ich bin ein Link im Inline-Stil](https://www.google.com)

[Ich bin ein Link im Inline-Stil mit Titel](https://www.google.com "Google's Homepage")

[Ich bin ein Link im Referenzstil][Beliebiger Referenztext ohne Berücksichtigung der Groß-/Kleinschreibung]

[Ich bin ein relativer Verweis auf eine Repository-Datei](../blob/master/LICENSE)

[Sie können Zahlen für referenzähnliche Link-Definitionen verwenden][1]

Oder lassen Sie es leer und verwenden Sie den [Linktext selbst].

URLs und URLs in spitzen Klammern werden automatisch in Links umgewandelt.
http://www.example.com oder <http://www.example.com> und manchmal
example.com (aber nicht auf Github, zum Beispiel).

Etwas Text, um zu zeigen, dass die Referenzlinks später folgen können.

[beliebiger Referenztext ohne Berücksichtigung der Groß- und Kleinschreibung]: https://www.themefisher.com
[1]: https://gethugothemes.com
[Linktext selbst]: https://www.getjekyllthemes.com

<hr>

##### Paragraph

Lorem ipsum dolor sit amet consectetur adipisicing elit. Quam nihil enim maxime corporis cumque totam aliquid nam sint inventore optio modi neque laborum officiis necessitatibus, facilis placeat pariatur! Voluptatem, sed harum pariatur adipisci voluptates voluptatum cumque, porro sint minima similique magni perferendis fuga! Optio vel ipsum excepturi tempore reiciendis id quidem? Vel in, doloribus debitis nesciunt fugit sequi magnam accusantium modi neque quis, vitae velit, pariatur harum autem a! Velit impedit atque maiores animi possimus asperiores natus repellendus excepturi sint architecto eligendi non, omnis nihil. Facilis, doloremque illum. Fugit optio laborum minus debitis natus illo perspiciatis corporis voluptatum rerum laboriosam.

<hr>

##### Geordnete Liste

1. Listeneintrag
2. Listeneintrag
3. Listeneintrag
4. Listeneintrag
5. Listeneintrag

<hr>

##### Ungordnete Liste

* Listeneintrag
* Listeneintrag
* Listeneintrag
* Listeneintrag
* Listeneintrag

<hr>

##### Code und Syntax Highlighting

Inline `code` ist von `backticks` umgeben.

```javascript
var s = "JavaScript syntax highlighting";
alert(s);
```
 
```python
s = "Python syntax highlighting"
print s
```

<hr>

##### Zitat

> Dies ist ein Beispiel Zitat.

<hr>

##### Inline HTML

Sie können auch rohes HTML in Ihrem Markdown verwenden, und es wird meistens ziemlich gut funktionieren.

<dl>
  <dt>Definitionsliste</dt>
  <dd>Lorem Ipsum</dd>

  <dt>Markdown in HTML</dt>
  <dd>Funktioniert *nicht* **sehr** gut. Verwenden Sie HTML <em>Tags</em>.</dd>
</dl>


<hr>

##### Tabellen

Doppelpunkte können verwendet werden, um Spalten auszurichten.

| Tables            | Are                 | Cool  |
| ----------------- |:-------------------:| -----:|
| spalte 3 ist      | rechts ausgerichtet | $1600 |
| spalte 2 ist      | centered            |   $12 |
| zebrastreifen     | sind nett           |    $1 |

Jede Kopfzelle muss durch mindestens 3 Bindestriche voneinander getrennt sein.
Die äußeren Pipes (|) sind optional, und Sie müssen nicht dafür sorgen, dass das 
rohen Markdown nicht aufhübschen. Sie können auch Inline-Markdown verwenden.

Markdown | Weniger | Schön
--- | --- | ---
*trotzdem* | `schön` | **dargestellt**
1 | 2 | 3

<hr>

##### Bilder

![image](../../images/blog/post-6.jpg)

<hr>

##### Youtube video

{{< youtube C0DPdy98e4c >}}