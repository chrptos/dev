## 初級

### Pick
組み込みの型ユーティリティPick<T, K>を使用せず、TからKのプロパティを抽出する型を実装します。
```typescript
interface Todo {
  title: string
  description: string
  completed: boolean
}

type TodoPreview = MyPick<Todo, 'title' | 'completed'>

const todo: TodoPreview = {
    title: 'Clean room',
    completed: false,
}
```

TypeScriptでは、独自の型ユーティリティを作成することができます。既存の`Pick`型ユーティリティを使わずに、同じ機能を持つ独自の型ユーティリティ`MyPick`を作成するには、以下のように行います：
```typescript
type MyPick<T, K extends keyof T> = {
    [P in K]: T[P];
}

interface Todo {
    title: string;
    description: string;
    completed: boolean;
}

type TodoPreview = MyPick<Todo, 'title' | 'completed'>;

const todo: TodoPreview = {
    title: 'Clean room',
    completed: false,
}
```

ここで、`MyPick`は2つの型引数を取ります。`T`は任意の型、`K`は`T`のキーのうちの一部または全部を表します。その内部ではマッピング型を使っています。`[P in K]: T[P];` は `K`のすべてのキー（つまりプロパティ）を列挙し、それらのキーに対する`T`のプロパティ型を取得します。これにより、新たに選択されたプロパティだけを持つ新しい型を作成します。

この方法を使用すれば、任意のオブジェクト型から任意のプロパティを選択する型ユーティリティを作成することができます。

TIPS: 
これらの `T`, `K`, `P` はジェネリック型パラメータです。TypeScriptでは、ジェネリックを使って柔軟で再利用可能なコードを書くことができます。具体的には：

- `T` は "Type" の略で、一般的なデータ型を表します。それは何でもあり得ます：`string`、`number`、`Array<string>`、カスタムインターフェイスなどです。

- `K` は "Key" の略で、オブジェクトのキー（プロパティ名）を表します。`K extends keyof T` は `K` が `T` のキーであることを示しています。つまり、`K` は `T` のプロパティ名の一部または全部を表します。

- `P` は "Property" の略で、ここではマッピング型の一部として使用されています。`[P in K]: T[P]` は `K` のすべてのキー（つまりプロパティ）を列挙し、それらのキーに対する `T` のプロパティ型を取得しています。

このように、`T`, `K`, `P` はいずれも型のプレースホルダーであり、実際の型（またはキー）に置き換えられます。これらのパラメータを使うことで、関数やクラス、インターフェイス、型などが任意の型で動作するようにすることができ、それによりコードの再利用性と柔軟性が高まります。

`[P in K]: T[P]`はTypeScriptのマッピング型の一部で、型`T`から新しい型を作成します。マッピング型はオブジェクト型の各プロパティを新たな型にマップします。`[P in K]: T[P]`の処理の順番は次の通りです：

1. **`P in K`によるイテレーション**: `K`はジェネリック型であり、一連のキー（プロパティ名）を表します。`P in K`はこれらのキーに対するイテレーションを表し、`P`はそのイテレーションの現在のキーを表します。

2. **`T[P]`によるプロパティ型の取得**: `T`はオブジェクト型を表すジェネリック型で、`T[P]`は`T`の`P`という名前のプロパティの型を取得します。`P`は上記のイテレーションの現在のキーなので、この操作は各キーに対応するプロパティの型を取得します。

3. **新たな型の作成**: `[P in K]: T[P]`全体は、`K`の各キーに対応する`T`のプロパティ型からなる新たな型を作成します。

例えば、`T`が`{ a: number, b: string, c: boolean }`、`K`が`"a" | "b"`である場合、`[P in K]: T[P]`は次のように処理されます：

- `P in K`のイテレーションでは、まず`P`が`"a"`になります。その次に、`P`が`"b"`になります。
- `T[P]`は各`P`に対応する`T`のプロパティ型を取得します。まず`T["a"]`（つまり`number`）が取得され、次に`T["b"]`（つまり`string`）が取得されます。
- 最終的に、新たな型`{ a: number, b: string }`が作成されます。


### Readonly 
組み込みの型ユーティリティPick<T, K>を使用せず、TからKのプロパティを抽出する型を実装します。
```typescript
interface Todo {
  title: string
  description: string
}

const todo: MyReadonly<Todo> = {
  title: "Hey",
  description: "foobar"
}

todo.title = "Hello" // Error: cannot reassign a readonly property
todo.description = "barFoo" // Error: cannot reassign a readonly property
```

上記の問題では、すべてのプロパティを読み取り専用にしたい型 `MyReadonly<T>` を作成したいとのことです。この場合、組み込みの型ユーティリティ `Readonly<T>` は使用しないとの指定があります。
次のように定義することで、この型ユーティリティを実装できます。
```typescript
type MyReadonly<T> = {
  readonly [P in keyof T]: T[P]
}
```
ここでは、マッピング型を使っています。`[P in keyof T]: T[P]` の部分で、`T` のすべてのプロパティを一つずつ取り出し (`P in keyof T`）、それぞれのプロパティを読み取り専用 (`readonly`) にして、元の型 `T` の同名のプロパティと同じ型 (`T[P]`) を指定しています。
この `MyReadonly<T>` 型を使用すると、元のオブジェクト型 `T` のすべてのプロパティが読み取り専用になります。したがって、読み取り専用のプロパティに値を再代入しようとすると、TypeScriptのコンパイラはエラーを報告します。


### Tuple to Object
タプルを受け取り、その各値のkey/valueを持つオブジェクトの型に変換する型を実装します。
```typescript
const tuple = ['tesla', 'model 3', 'model X', 'model Y'] as const

type result = TupleToObject<typeof tuple> // expected { tesla: 'tesla', 'model 3': 'model 3', 'model X': 'model X', 'model Y': 'model Y'}
```
この問題では、タプルの各値をキーと値に持つオブジェクトの型を生成する型 `TupleToObject<T>` を作成します。

次のように定義することで、この型を実装できます：

```typescript
type TupleToObject<T extends readonly string[]> = {
  [K in T[number]]: K
}
```

この型では、マッピング型とインデックス型を使用しています：

1. `T extends readonly string[]`：この部分は、ジェネリック型 `T` が任意のキーのタプルであることを示しています。`readonly` 修飾子は、タプルが変更不可能であることを示しています。

2. `[K in T[number]]: K`：この部分は、タプル `T` の各要素（文字列リテラル）を一つずつ取り出し (`K in T[number]`）、その要素をキーと値にする新しいオブジェクトの型を作成しています。

この `TupleToObject<T>` 型を使用すると、元のタプルの各要素がキーと値になる新しいオブジェクトの型が作成されます。

それぞれについて具体的な例を挙げてみます。

まず、次のようなタプルを考えます：

```typescript
type TupleType = ['a', 'b', 'c'];
```

ここで、`[K in T]: K`の形式を使用すると、キーはタプルのインデックス（すなわち、数値）となります：

```typescript
type Result1 = {
  [K in TupleType]: K;
};

// 上記は次の型になります：
type Result1 = {
  0: 0;
  1: 1;
  2: 2;
};
```

この例では、マッピング型がタプルのインデックス（数値）をキーとして使用しています。

一方、`[K in T[number]]: K`の形式を使用すると、キーはタプルの要素（この場合は文字列）となります：

```typescript
type Result2 = {
  [K in TupleType[number]]: K;
};

// 上記は次の型になります：
type Result2 = {
  a: 'a';
  b: 'b';
  c: 'c';
};
```

この例では、マッピング型がタプルの要素（文字列）をキーとして使用しています。

したがって、`[K in T]: K`と`[K in T[number]]: K`は、キーとして使用する値（インデックスまたは要素）によって、異なる結果を生成します。

T[number]は公式ドキュメントでは、なんと呼ばれている？
TypeScriptの公式ドキュメントでは、`T[number]` のような表記を「インデックスアクセス型」（Index Access Types）と呼んでいます。

インデックスアクセス型はオブジェクトのプロパティや配列の要素にアクセスするための型です。`T[number]` の場合、`T` は配列やタプル、`number` はその要素のインデックスを表しています。

この機能は、配列やタプルの要素の型を抽出するのに特に有用です。また、オブジェクトの特定のプロパティの型を抽出するためにも使用されます。

例：

```typescript
type Todo = {
  id: number;
  text: string;
  completed: boolean;
};

type TodoText = Todo['text']; // string
type TodoKeys = keyof Todo; // "id" | "text" | "completed"
```

この例では、`Todo['text']`は`Todo`オブジェクトの`text`プロパティの型（`string`）を抽出しています。`keyof Todo`は`Todo`オブジェクトの全てのプロパティ名（キー）の型を抽出しています。

### First of Array
配列Tを受け取り、その最初のプロパティの型を返すFirst<T>を実装します。
```typescript
type arr1 = ['a', 'b', 'c']
type arr2 = [3, 2, 1]

type head1 = First<arr1> // expected to be 'a'
type head2 = First<arr2> // expected to be 3
```
以下のように `First<T>` 型を実装することができます：

```typescript
type First<T extends any[]> = T extends [infer U, ...any[]] ? U : never;
```

この実装では `infer` キーワードと配列のレストパラメータ構文 (`...any[]`) を使用しています。

この `infer` キーワードは条件型の中で新しい型変数を導入するためのものです。`T` が `[infer U, ...any[]]` 型に割り当て可能な場合、`U` は `T` の最初の要素の型を表します。

したがって、`T extends [infer U, ...any[]] ? U : never` は、「もし `T` が配列（少なくとも1つの要素を持つ）なら、その最初の要素の型を返し、そうでなければ `never` を返す」という意味になります。

この実装により、`First<arr1>` は `'a'` となり、`First<arr2>` は `3` となります。

inferを利用すると型での条件分岐ができるようになる。
https://qiita.com/ehika/items/8f41d4a3c8f9df4af9c3


### Length of Tuple
タプルTを受け取り、そのタプルの長さを返す型Length<T>を実装します。
```typescript
type tesla = ['tesla', 'model 3', 'model X', 'model Y']
type spaceX = ['FALCON 9', 'FALCON HEAVY', 'DRAGON', 'STARSHIP', 'HUMAN SPACEFLIGHT']

type teslaLength = Length<tesla>  // expected 4
type spaceXLength = Length<spaceX> // expected 5
```
はい、その通りです。

TypeScriptでは、配列型を表すために `any[]` を使うことができますが、この型は配列の要素を変更することが可能なため、タプルに対してこの型を使うと問題が生じることがあります。なぜなら、タプルは要素の追加や削除、変更ができない（つまりイミュータブルである）べきであるからです。

したがって、タプルの長さを取得するための型を実装する場合には、`readonly any[]` を使ってタプルがイミュータブルであることを明示するべきです：

```typescript
type Length<T extends readonly any[]> = T['length'];
```

この実装により、`T` はイミュータブルな配列またはタプルを表し、`T['length']` でその長さ（要素数）を取得します。この型を使うと、タプルの長さをコンパイル時に確定することができます。

### Exclude