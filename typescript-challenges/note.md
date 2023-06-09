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
組み込みの型ユーティリティExclude <T, U>を使用せず、Uに割り当て可能な型をTから除外する型を実装します。
```typescript
type Result = MyExclude<'a' | 'b' | 'c', 'a'> // 'b' | 'c'
```
組み込みの型ユーティリティ`Exclude<T, U>`を使用せずに、`U`に割り当て可能な型を`T`から除外する`MyExclude<T, U>`型は、条件型を使って以下のように実装できます：

```typescript
type MyExclude<T, U> = T extends U ? never : T;
```

この実装では、`T extends U ? never : T`という条件型を使用しています。これは、「もし`T`が`U`に割り当て可能なら`never`を返し、そうでなければ`T`をそのまま返す」という意味になります。`never`は型システムの底部に位置する型で、どの型にも割り当てることができません。

したがって、この実装では、`T`の各型について`U`に割り当て可能かどうかをチェックし、割り当て可能な型は`never`になり、その他の型はそのまま残ります。これにより、`U`に割り当て可能な型が`T`から除外されます。

例えば、`MyExclude<'a' | 'b' | 'c', 'a'>`とすると、`'a'`, `'b'`, `'c'`の各型について`'a'`に割り当て可能かどうかをチェックします。`'a'`は`'a'`に割り当て可能なので`never`になり、`'b'`と`'c'`は`'a'`に割り当て不可能なのでそのまま残ります。その結果、`'b' | 'c'`が得られます。

### Awaited
Promise ライクな型が内包する型をどのように取得すればよいでしょうか。

例えば：Promise<ExampleType>という型がある場合、どのようにして ExampleType を取得すればよいでしょうか。
```typescript
type ExampleType = Promise<string>

type Result = MyAwaited<ExampleType> // string
```

### If
条件値C、 Cが truthy である場合の戻り値の型T、Cが falsy である場合の戻り値の型Fを受け取るIfを実装します。 条件値C はtrueかfalseのどちらかであることが期待されますが、T と F は任意の型をとることができます。
```typescript
type A = If<true, 'a', 'b'>; // expected to be 'a'
type B = If<false, 'a', 'b'>; // expected to be 'b'
```

### Concat 
JavaScript のArray.concat関数を型システムに実装します。この型は 2 つの引数を受け取り、受け取ったイテレータの要素を順に含む新しい配列を返します。
```typescript
type Concat<T extends readonly unknown[], U extends readonly unknown[]> = [...T, ...U];
```
TIPS:unknownはどういった型ですか
TypeScriptにおける`unknown`型は、可能な型が何であるかを事前に知らない値を表現するための型です。これは`any`型に似ていますが、`unknown`型はより型安全です。

`any`型を使用すると、TypeScriptの型システムはその値に対して何でも許可します。それは、プロパティへのアクセス、関数の呼び出し、新しい値への代入など、あらゆる操作が可能ということです。このため、`any`型を使用すると型エラーが発生しやすくなります。

一方、`unknown`型を使用すると、その値に対する操作はほぼ全てが制限されます。`unknown`型の値を他の何かに割り当てる前に、その値の型を具体的に確認する必要があります（これを型ガードと言います）。

したがって、`unknown`は不明な型の値を安全に扱うための手段を提供します。`unknown`型の値に対して何かをする前に、その値が期待する型であることを確認することを強制します。

たとえば、以下のコードはエラーになります：

```typescript
let value: unknown;
value.foo;  // Error: Object is of type 'unknown'.
```

型ガードを使用して型を確認すれば、その値を安全に操作できます：

```typescript
let value: unknown;

if (typeof value === 'object' && value !== null) {
  // Now TypeScript knows that `value` is an object.
  console.log(value.foo);
}
```
https://recursionist.io/learn/languages/typescript/introduction/any-unknown#:~:text=TypeScript%20unknown%E5%9E%8B&text=any%E5%9E%8B%E3%81%A8unknown%E5%9E%8B%E3%81%AE%E5%A4%A7%E3%81%8D%E3%81%AA%E9%81%95%E3%81%84%E3%81%AF%E3%80%81any,%E3%82%92%E8%A1%8C%E3%81%86%E3%81%93%E3%81%A8%E3%81%8C%E3%81%A7%E3%81%8D%E3%81%BE%E3%81%9B%E3%82%93%E3%80%82


### Includes
JavaScriptのArray.include関数を型システムに実装します。この型は、2 つの引数を受け取り、trueやfalseを出力しなければなりません。
```typescript
type isPillarMen = Includes<['Kars', 'Esidisi', 'Wamuu', 'Santana'], 'Dio'> // expected to be `false`
```

### Push
Array.pushのジェネリックバージョンを実装します。
```typescrip
type Result = Push<[1, 2], '3'> // [1, 2, '3']
```
配列に新しい要素を追加する`Push`型を実装するには、TypeScript のタプルとスプレッド演算子を利用します。以下のように定義できます。

```typescript
type Push<T extends readonly any[], V> = [...T, V];
```

この`Push`型は2つのジェネリック型引数`T`と`V`を受け取ります。

`T`は任意の要素を持つ配列（またはタプル）、`V`は配列に追加したい新しい要素です。

そして、`[...T, V]`は新しい配列を作成します。この新しい配列は`T`の全ての要素と新しい要素`V`を含みます。

したがって、この`Push`型は、配列`T`に新しい要素`V`を追加した結果を返します。

### Unshift
Array.unshiftの型バージョンを実装します。
```typescript
type Result = Unshift<[1, 2], 0> // [0, 1, 2,]
```
配列の先頭に新しい要素を追加する`Unshift`型を実装するには、TypeScript のタプルとスプレッド演算子を利用します。以下のように定義できます。

```typescript
type Unshift<T extends readonly any[], V> = [V, ...T];
```

この`Unshift`型は2つのジェネリック型引数`T`と`V`を受け取ります。

`T`は任意の要素を持つ配列（またはタプル）、`V`は配列の先頭に追加したい新しい要素です。

そして、`[V, ...T]`は新しい配列を作成します。この新しい配列は新しい要素`V`と`T`の全ての要素を含みます。

したがって、この`Unshift`型は、配列`T`の先頭に新しい要素`V`を追加した結果を返します。

### Parameters 
組み込みの型ユーティリティParameters<T>を使用せず、Tからタプル型を構築する型を実装します。
```typescript
const foo = (arg1: string, arg2: number): void => {}

type FunctionParamsType = MyParameters<typeof foo> // [arg1: string, arg2: number]
```
関数のパラメータのタプル型を取得する`MyParameters`型を実装するには、TypeScriptの高度な型システム、特に条件付き型と`infer`キーワードを使用します。以下のように定義できます。

```typescript
type MyParameters<T> = T extends (...args: infer P) => any ? P : never;
```

この`MyParameters`型はジェネリック型引数`T`を受け取ります。ここで`T`は任意の関数型を表します。

そして、`T extends (...args: infer P) => any ? P : never`は、`T`が関数である場合（つまり`(...args: infer P) => any`の形を持つ場合）に、その関数のパラメータのタプル型`P`を返します。そうでなければ`never`型を返します。

この定義では、`infer P`を使用して`T`のパラメータのタプル型を推論（inferring）します。

したがって、この`MyParameters`型は、関数`T`のパラメータのタプル型を返します。