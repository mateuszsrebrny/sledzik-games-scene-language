# ŚGSL Extension Proposal: Parametric Components and Instances

## Cel

Dodać do ŚGSL możliwość definiowania wieloczęściowych, wielokrotnie używalnych elementów sceny.

Przykłady:

- okno fabryczne,
- cysterna,
- drzwi garażowe,
- pompa,
- półka,
- cała hala fabryczna.

Każdy komponent może mieć własny zestaw parametrów.

Nie wprowadzamy osobnej konstrukcji `copy`.

Każde użycie `instance` tworzy nową kopię komponentu.

---

# Główne pojęcia

## Component

`component` definiuje wieloczęściowy element.

Definicja komponentu:

- może zawierać wiele obiektów,
- może deklarować własne parametry,
- używa lokalnego układu współrzędnych,
- sama nie tworzy niczego w scenie.

## Instance

`instance` tworzy egzemplarz komponentu w scenie.

Każda instancja:

- jest niezależną kopią komponentu,
- może mieć własną pozycję,
- może mieć własny obrót,
- może nadpisywać parametry komponentu.

---

# Dlaczego nie potrzebujemy `copy`

To:

```sgsl
instance Window01 FactoryWindow
    at -4 4 -9

instance Window02 FactoryWindow
    at 0 4 -9

instance Window03 FactoryWindow
    at 4 4 -9
```

już tworzy trzy kopie tego samego komponentu.

Jeżeli jedna kopia ma mieć inne wymiary:

```sgsl
instance Window04 FactoryWindow
    at 8 4 -9

    set width 4.5
```

Nie potrzeba osobnego mechanizmu `copy`.

---

# Składnia komponentu

```sgsl
component <ComponentName>
    param <ParameterName> <DefaultValue>
    param <ParameterName> <DefaultValue>

    <object declarations>
```

Przykład:

```sgsl
component FactoryWindow
    param width 3.0
    param height 2.0
    param frameThickness 0.20
    param glassThickness 0.05

    block TopFrame
        at 0 (height / 2 - frameThickness / 2) 0
        size width frameThickness glassThickness
        color darkgray

    block BottomFrame
        at 0 (-height / 2 + frameThickness / 2) 0
        size width frameThickness glassThickness
        color darkgray

    block LeftFrame
        at (-width / 2 + frameThickness / 2) 0 0
        size frameThickness (height - 2 * frameThickness) glassThickness
        color darkgray

    block RightFrame
        at (width / 2 - frameThickness / 2) 0 0
        size frameThickness (height - 2 * frameThickness) glassThickness
        color darkgray

    block Glass
        at 0 0 0
        size (width - 2 * frameThickness) (height - 2 * frameThickness) glassThickness
        color lightblue
```

---

# Parametry

Komponent sam definiuje swój interfejs parametrów.

Przykład dla okna:

```sgsl
param width 3.0
param height 2.0
param frameThickness 0.20
param glassThickness 0.05
```

Przykład dla cysterny:

```sgsl
param radius 2.0
param bodyHeight 7.0
param baseHeight 0.5
param roofHeight 0.8
```

Parametry:

- są lokalne dla komponentu,
- mają wartość domyślną,
- mogą być używane w wyrażeniach,
- mogą być nadpisane przez instancję.

Nie definiujemy uniwersalnych parametrów typu `width`, `height` czy `depth` dla wszystkich komponentów.

Każdy komponent deklaruje tylko to, czego sam potrzebuje.

---

# Instancje

Składnia:

```sgsl
instance <InstanceName> <ComponentName>
    at X Y Z
    rotate X Y Z
    set <ParameterName> <Value>
```

Przykład podstawowy:

```sgsl
instance FrontWindow01 FactoryWindow
    at -4 4 -9
```

Przykład z parametrami:

```sgsl
instance FrontWindow02 FactoryWindow
    at 0 4 -9

    set width 4.0
    set height 2.4
    set frameThickness 0.25
```

Przykład obrócony:

```sgsl
instance SideWindow01 FactoryWindow
    at -9 4 0
    rotate 0 90 0
```

---

# Domyślne wartości instancji

Jeżeli pominięto `at`:

```text
at 0 0 0
```

Jeżeli pominięto `rotate`:

```text
rotate 0 0 0
```

Jeżeli parametr nie został nadpisany przez `set`, używana jest wartość domyślna z definicji komponentu.

---

# Lokalny układ współrzędnych

Każdy komponent ma własny lokalny układ współrzędnych.

```text
(0, 0, 0)
```

jest początkiem komponentu.

Przykład:

```sgsl
component SimpleMachine
    block Body
        at 0 1 0
        size 2 2 2
        color gray
```

Instancja:

```sgsl
instance Machine01 SimpleMachine
    at 10 0 -5
```

Bez rotacji `Body` znajdzie się w pozycji:

```text
(10, 1, -5)
```

Czyli:

```text
world position = instance position + local position
```

---

# Transformacja instancji

Instancja przesuwa i obraca wszystkie elementy komponentu jako całość.

Transformacja końcowa:

```text
world transform =
instance transform × local object transform
```

Kolejność:

1. oblicz geometrię lokalną komponentu,
2. rozwiąż lokalne anchory obiektów,
3. zastosuj lokalne rotacje obiektów,
4. zastosuj rotację całej instancji,
5. zastosuj pozycję instancji.

---

# Obrót

`rotate` instancji obraca cały komponent wokół jego lokalnego początku `(0, 0, 0)`.

Przykład:

```sgsl
instance SideWindow FactoryWindow
    at -9 4 0
    rotate 0 90 0
```

Wszystkie części okna obracają się razem.

Lokalne `rotate` na częściach wewnątrz komponentu nadal działa.

---

# Anchor

Obiekty wewnątrz komponentu mogą używać zwykłego `anchor`.

Przykład:

```sgsl
component MachineBase
    block Body
        anchor center bottom center
        at 0 0 0
        size 3 4 2
        color gray
```

Anchor jest rozwiązywany w lokalnym układzie komponentu.

Dla samej instancji w v1 `at` oznacza położenie lokalnego początku komponentu.

Nie obliczamy automatycznie bounding boxa komponentu.

---

# Wyrażenia matematyczne

Komponenty parametryczne wymagają prostych wyrażeń matematycznych.

Obsługiwane operacje:

```text
+
-
*
/
()
```

Wyrażenia mogą zawierać:

- liczby,
- parametry bieżącego komponentu,
- nawiasy.

Przykłady:

```sgsl
size (width - 2 * frameThickness) height glassThickness
```

```sgsl
at 0 (height / 2 - frameThickness / 2) 0
```

```sgsl
radius (radius + 0.15)
```

Nie używać Pythonowego `eval()`.

Wyrażenia powinny być parsowane przez Lark i oceniane przez bezpieczny evaluator.

---

# Rozwiązywanie parametrów

Dla instancji:

```sgsl
instance LargeWindow FactoryWindow
    set width 4.5
```

pipeline powinien wyglądać tak:

1. Pobierz domyślne parametry komponentu.
2. Nadpisz wartości podane przez `set`.
3. Zweryfikuj nazwy parametrów.
4. Oceń wszystkie wyrażenia w obiektach komponentu.
5. Utwórz rozwinięte obiekty lokalne.
6. Zastosuj transformację instancji.
7. Przekaż zwykłą geometrię rendererom.

---

# Nieznany parametr

To powinien być błąd:

```sgsl
instance Window01 FactoryWindow
    set tankRadius 4
```

jeżeli komponent `FactoryWindow` nie deklaruje `tankRadius`.

Przykładowy komunikat:

```text
Instance 'Window01' of component 'FactoryWindow'
sets unknown parameter 'tankRadius'.

Available parameters:
width, height, frameThickness, glassThickness
```

---

# Brak komponentu

To powinien być błąd:

```sgsl
instance Window01 MissingWindow
```

Przykładowy komunikat:

```text
Instance 'Window01' references unknown component 'MissingWindow'.
```

---

# Nazwy

Nazwy komponentów muszą być unikalne w pliku.

Nazwy instancji muszą być unikalne w scenie.

Nazwy części wewnątrz jednego komponentu muszą być unikalne w obrębie tego komponentu.

Dozwolone jest, aby różne komponenty posiadały część o tej samej nazwie, np. `Body`.

---

# Hierarchia nazw

Instancja:

```sgsl
instance Window01 FactoryWindow
```

powinna logicznie tworzyć:

```text
Window01
├── TopFrame
├── BottomFrame
├── LeftFrame
├── RightFrame
└── Glass
```

W płaskim modelu sceny nazwy mogą wyglądać tak:

```text
Window01.TopFrame
Window01.BottomFrame
Window01.LeftFrame
Window01.RightFrame
Window01.Glass
```

W Robloxie instancja powinna być generowana jako `Model` o nazwie `Window01`.

---

# Definicje komponentów a scena

Definicja:

```sgsl
component FactoryWindow
    ...
```

nie tworzy geometrii.

Geometria pojawia się dopiero przez:

```sgsl
instance Window01 FactoryWindow
    ...
```

Komponent może być zdefiniowany przed lub po scenie, zależnie od implementacji parsera.

Preferowane zachowanie:

- zebrać wszystkie definicje komponentów,
- następnie rozwijać instancje.

---

# Zagnieżdżanie komponentów

W v1 komponent może zawierać tylko prymitywy:

- `block`,
- `cylinder`,
- `frustum`.

Komponent nie może jeszcze zawierać `instance` innego komponentu.

Czyli na razie niedozwolone:

```sgsl
component FactoryHall
    instance Window01 FactoryWindow
        at 0 4 -9
```

Zagnieżdżone komponenty można dodać w kolejnej wersji.

Powód:

- prostszy parser,
- brak cyklicznych zależności,
- łatwiejsze debugowanie,
- łatwiejsza walidacja transformacji.

---

# Rekurencja

Komponent nigdy nie może instancjonować samego siebie, bezpośrednio ani pośrednio.

Gdy zagnieżdżanie zostanie dodane w przyszłości, parser powinien wykrywać cykle.

Nie jest to wymagane w v1, ponieważ komponenty nie mogą zawierać instancji.

---

# Materiały, kolory i overrides

Obiekty wewnątrz komponentu używają tych samych właściwości co zwykłe obiekty:

```text
color
material
anchor
rotate
override
```

Przykład:

```sgsl
component RoofPumpPlaceholder
    param width 2
    param height 2
    param depth 2

    block Placeholder
        at 0 0 0
        size width height depth
        color gray
        override roblox RoofPump01
```

Każda instancja komponentu zachowuje override.

---

# Internal scene model

Przykładowa definicja:

```json
{
  "type": "component_definition",
  "name": "FactoryWindow",
  "parameters": {
    "width": 3.0,
    "height": 2.0,
    "frameThickness": 0.2,
    "glassThickness": 0.05
  },
  "objects": [
    {
      "type": "block",
      "name": "TopFrame"
    }
  ]
}
```

Przykładowa instancja:

```json
{
  "type": "component_instance",
  "name": "Window01",
  "component": "FactoryWindow",
  "at": [0, 4, -9],
  "rotation": [0, 0, 0],
  "parameter_overrides": {
    "width": 4.0
  }
}
```

Po rozwinięciu komponentów renderery powinny otrzymać zwykłe obiekty geometrii.

Renderery nie powinny implementować parametrów ani instancji.

---

# Pipeline

Preferowany pipeline:

```text
ŚGSL source
    ↓
Lark parser
    ↓
component definitions + scene statements
    ↓
validation
    ↓
parameter resolver
    ↓
component expander
    ↓
local anchor resolver
    ↓
instance transform resolver
    ↓
flat scene objects
    ↓
HTML renderer / Roblox renderer
```

Komponenty powinny być rozwijane we wspólnej warstwie, zanim dane dotrą do rendererów.

Dzięki temu HTML i Roblox zawsze otrzymują tę samą geometrię.

---

# Grammar — propozycja

Schematycznie:

```lark
start: scene

scene: "scene" NAME statement*

statement: object
         | component
         | instance

component: "component" NAME component_statement*

component_statement: param
                   | object

param: "param" NAME expression

instance: "instance" NAME NAME instance_property*

instance_property: at
                 | rotate
                 | set_param

set_param: "set" NAME expression
```

Obecne reguły `object` obejmują:

```text
block
cylinder
frustum
```

Dokładna składnia może zostać dopasowana do obecnej gramatyki.

---

# Backward compatibility

Rozszerzenie jest w pełni zgodne wstecz.

Istniejące pliki bez:

- `component`,
- `param`,
- `instance`,
- `set`,
- wyrażeń parametrycznych

działają bez zmian.

---

# Kompletny przykład

```sgsl
scene FactoryWindowDemo

component FactoryWindow
    param width 3.0
    param height 2.0
    param frameThickness 0.20
    param glassThickness 0.05

    block TopFrame
        at 0 (height / 2 - frameThickness / 2) 0
        size width frameThickness glassThickness
        color darkgray

    block BottomFrame
        at 0 (-height / 2 + frameThickness / 2) 0
        size width frameThickness glassThickness
        color darkgray

    block LeftFrame
        at (-width / 2 + frameThickness / 2) 0 0
        size frameThickness (height - 2 * frameThickness) glassThickness
        color darkgray

    block RightFrame
        at (width / 2 - frameThickness / 2) 0 0
        size frameThickness (height - 2 * frameThickness) glassThickness
        color darkgray

    block Glass
        at 0 0 0
        size (width - 2 * frameThickness) (height - 2 * frameThickness) glassThickness
        color lightblue

instance FrontWindow01 FactoryWindow
    at -4 4 -9

instance FrontWindow02 FactoryWindow
    at 0 4 -9

    set width 4.0
    set height 2.4

instance FrontWindow03 FactoryWindow
    at 4 4 -9

instance SideWindow01 FactoryWindow
    at -9 4 0
    rotate 0 90 0

    set width 3.5
    set frameThickness 0.25
```

---

# Przykład cysterny

```sgsl
component StorageTank
    param radius 2.0
    param bodyHeight 7.0
    param bottomHeight 0.5
    param roofHeight 0.8
    param roofTopRadius 0.4

    cylinder Bottom
        at 0 (bottomHeight / 2) 0
        radius (radius + 0.15)
        height bottomHeight
        color darkgray

    cylinder Body
        at 0 (bottomHeight + bodyHeight / 2) 0
        radius radius
        height bodyHeight
        color white

    frustum Roof
        at 0 (bottomHeight + bodyHeight + roofHeight / 2) 0
        bottomRadius radius
        topRadius roofTopRadius
        height roofHeight
        color gray

instance Tank01 StorageTank
    at -14 0 0

instance Tank02 StorageTank
    at -9 0 0

instance Tank03 StorageTank
    at -4 0 0

    set radius 2.5
    set bodyHeight 9.0
```

---

# Kryteria ukończenia

Implementacja jest poprawna, jeśli:

1. Można zdefiniować komponent zawierający wiele prymitywów.
2. Definicja komponentu sama nie tworzy geometrii.
3. Każda instancja tworzy niezależną kopię komponentu.
4. Komponent może deklarować dowolne własne parametry.
5. Parametry mają wartości domyślne.
6. Instancja może nadpisywać parametry przez `set`.
7. Nieznany parametr powoduje czytelny błąd.
8. Wyrażenia obsługują podstawową arytmetykę.
9. Wszystkie części instancji przesuwają się razem.
10. Wszystkie części instancji obracają się razem.
11. Lokalne rotacje części nadal działają.
12. Anchory części są rozwiązywane lokalnie.
13. HTML i Roblox otrzymują identyczną rozwiniętą geometrię.
14. Nazwy rozwiniętych części są jednoznaczne.
15. Istniejące pliki ŚGSL działają bez zmian.
16. Nie istnieje osobna konstrukcja `copy`.
