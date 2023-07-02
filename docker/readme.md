## ライフサイクル
image
created -> up <-> exited

## イメージ
download docker image 
`docker image pull <image_name>`

list docker images
`docker image ls <image>`

remove docker image
`docker image rm <image>`

## コンテナ
`docker container run {イメージ名}`
イメージからコンテナを作成して起動する。イメージがなければpullしてくる。

`docker container ls`
起動中のコンテナのみを表示

`docker container stop {コンテナ名}`
コンテナをexitedにする

`docker container restart {コンテナ名}`
コンテナをupする

`docker container rm {コンテナ名}`
コンテナを破棄する

## コンテナ操作

`-i`は、標準入力（stdin）を開いたままにし、コンテナのプロセスとホストのターミナルとの間で双方向の通信を可能にします。これにより、ユーザーはコンテナ内でコマンドを入力したり、対話型のアプリケーションを実行したりすることができます。

`-t`は、TTY（端末）を割り当てるためのものです。これにより、ユーザーはコンテナ内のプロセスとやり取りするために、ターミナルの特性を利用することができます。ターミナル特性には、カラーリングやカーソルの移動などが含まれます。

`docker run ubuntu -it bash`は、Dockerコマンドを使用して、Ubuntuの公式Dockerイメージから新しいコンテナを作成し、そのコンテナ内で対話型のBashシェルを実行するためのコマンドです。

具体的には、`docker run`はコンテナを実行するためのコマンドであり、ubuntuは使用するDockerイメージの名前です。-itオプションは、コンテナをインタラクティブモードで実行することを指定します。そして、bashは実行するコマンドであり、この場合はBashシェルを起動します。

つまり、上記のコマンドを実行すると、Dockerイメージから新しいUbuntuコンテナが作成され、そのコンテナ内でBashシェルが起動されます。ユーザーは対話的にコンテナ内でコマンドを実行したり、Bashシェルの機能を使用したりすることができます。

`docker image inspect ubuntu`でイメージの詳細な情報を知ることができる。

`docker container exec -it mycontainer bash`
`exec`コマンドを利用することで起動中のコンテナでコマンドを実行することができる。

`docker container run --name sukina-namae ubuntu`
`--name`とつけることで起動中のコンテナ名を好きに決めることができる。

`docker container prune`を利用することで、停止済みのコンテナをまとめて`rm`することができる。

`docker container run --rm ubuntu`とすると、デフォルトまたは指定したコマンドが実行されたあとに、使用済みのコンテナが自動的に削除される。

`docker container rm -f {コンテナ名}`とすると、起動中のコンテナも削除される。

`docker container run -d nginx`とすることでバックグラウンドで起動できる。`exec`も同じことできる。

`docker container attach nginx`とすることでフォアグラウンドに戻すことができる。

## シェルとは
人間 -> シェル -> OS(カーネル)
シェルは人間が理解できる操作を機械語に翻訳して、OSに伝えてくれるし、逆に機械から人間の分かる言葉にしてくれたりする。

## Dockerfile

- Dockerfileとは、自分好みのカスタマイズされたイメージを作成できる。
- ubuntu + nginxを利用したい場合など、imageをビルドにコマンドを実行したりなど
- ubuntu + python や ubuntu + node をベースイメージから構築できる
- いくらコンテナをカスタマイズしてもコンテナを作り直すと元に戻る。
- どこにでも同じ環境を再構築したいならコンテナの元になるイメージをカスタマイズすることで、コンテナのポータビリティを担保する。

`docker image build -t my-image:v1`
docker imageを自由に名前とタグをつけて作成することができる。

`docker image build .`
カレントディレクトリにあるDockerfileからイメージを作成する。

`RUN {好きなコマンド}`
イメージを作成した後に、RUNを実行した後のレイヤーをイメージに追加する。

`COPY {追加元} {追加先}`
ホストから好きなファイルをイメージに配置する。
もちろんコピーしただけなのでコンテナで編集しても同期しない

### ビルドコンテキスト
`docker image build {ディレクトリパス=ビルドコンテキスト}`
`image build`はDockerfileとビルドコンテキストからイメージを作成するコマンド

クライアント（docker CLI）
REST API
サーバー（docker デーモン）

別の場所にあっても動かせるようにREST APIが間に入っている
例えば、PCにクライアントがあって、クラウドホストにサーバー（デーモン）があっても動くように、という目的もある。

docker CLIはコンテキスト配下のファイルをすべてデーモン側に送り付ける。というのも`COPY`コマンドなどでコピーする元のファイルはdocker デーモンに送られている

ビルドコンテキストはビルドするときにDockerデーモンへ送られる

なので、COPY ../hello.text / など指定してもエラーになる。

ただし、dockerfileを別途しているすることでエラーを回避できる
`docker image build -f docker/Dockerfile . `
ビルドコンテキストにもあるし、Dockerfileも場所を指定しているのでbuildは成功する。

`.dockerignore`
ビルドコンテキストから除外したいファイルがある場合に指定可能

transfer contextで大きいファイルを指定するとbuildが遅くなるので、contextで指定するファイルはサイズを小さくすることを推奨

`CMD ["実行コマンド", "パラメータ1", "パラメータ2"]`
コンテナ実行時のデフォルトコマンドを設定する。ex) ubuntuだとbashコマンドがデフォルトになっている。
Dockerfileで1度しか使えない
複数のCMDがあるときは最後のCMDのみ有効
Dockerfileへ`CMD ["ls","-al"]`と指定すると
`docker image build .`
`docker container run <imageId>`で`ls -al`が実行されるはず

### レイヤー構造
イメージレイヤーはreadonly
Dockerfileに記述した命令ごとに層が増える
`docker image history <image_id>`でビルド後のレイヤーを確認できる。

レイヤーの数が多くなるほどイメージの容量が大きくなるので、コマンドをつなげることでイメージレイヤーを少なくする

レイヤーはキャッシュされるので、開発中はビルド時間を短くしたいのでRUNをたくさん記述してもいいかも

### その他、Dockerfileコマンド
ENV: 環境変数を指定可能
ARG: `ARG {キー1}={デフォルト値}`
RUNとrun: DockerfileのRUN命令はDockerイメージをビルドする際に使用され、一方でdocker runコマンドはそのイメージから新しいコンテナを作成して実行する際に使用されます。

ARGとENVの違い
argはイメージ作成時のみ有効
envはイメージ作成時だけでなく、コンテナ実行時も有効

`WORKDIR {ディレクトリパス}`
RUNやCMDなので作業ディレクトリを指定する
cdコマンドと同じ

## マルチステージビルド
ステージによって必要なソフトウェアが異なる
hello.c　コンパイル（gccイメージ）
COPY a.out
CMD ./a.out（ubuntuイメージ）
イメージビルドで作成されるイメージ
```
FROM gcc
...

FROM ubuntu
COPY --from=0 /app/a.out .

CMD ["./a.out"]
```
`--from=0`で1番目のステージからコピーするという意味

### マルチステージビルドのメリット
マルチステージビルドは、Dockerが提供する機能の一つで、単一のDockerfile内で複数のビルドステージを定義することができます。これにより、最終的なイメージのサイズを小さく保ちつつ、各ステージで異なるビルドと設定手順を使用することができます。

典型的な使用例は、ソースコードのコンパイルに必要なツールを含む大きなイメージを最初のステージで作成し、そのイメージを使ってアプリケーションをビルドし、最後にビルド成果物のみを軽量なベースイメージにコピーするというものです。これにより、実行時には開発ツールやビルド環境が必要なく、より小さなイメージを作成することができます。
```
# ビルドステージ
FROM golang:1.16 as builder

WORKDIR /app

# 必要なパッケージをダウンロード
COPY go.mod .
COPY go.sum .
RUN go mod download

# ソースコードをコピー
COPY . .

# ビルド実行
RUN CGO_ENABLED=0 GOOS=linux go build -o myapp .

# 実行ステージ
FROM alpine:latest

# ビルドステージから成果物をコピー
COPY --from=builder /app/myapp /myapp

# コンテナ起動時のコマンド
CMD ["/myapp"]
```
つまり、イメージのサイズを節約できるということ。
例えば、gccはコンパイラが入っている分、イメージサイズが大きくなる。
実行環境だけシンプルなubuntuで実行できる

開発環境やその他のビルドツールが含まれない差分でイメージが節約できる。

### マルチステージビルドで複数環境を管理する
Dockerfileをdev, prdでわける？
- 共通部分が二重管理になる
- ファイルが多くなり管理が煩雑になる
マルチステージビルドなら一つのDockerfileで管理することができる

```
FROM ubuntu AS base
RUN apt update
CMD ["sh", "-c", "echo My database is $database"]

FROM base AS development
ENV database=dev

FROM base AS production
ENV database=prd
```
`docker image build --target development .`

### そのほか
`CMD ["sh", "-c", "echo My database is $database"]`
この`CMD`命令はDockerfile内の一部であり、コンテナが起動されたときに実行するデフォルトのコマンドを定義しています。

具体的には、この行は`sh -c "echo My database is $database"`というコマンドを実行します。これは、シェル(`sh`)を使って`-c`オプションに続くコマンドを実行します。

このコマンドは`"echo My database is $database"`という部分を実行します。`echo`は標準出力にテキストを出力するコマンドで、ここでは`My database is`の後に`$database`という環境変数の値を出力します。つまり、コンテナが起動されたときに、`My database is `とその後に`$database`の値（環境変数`database`の値）を出力します。

この`$database`という環境変数は、通常、Dockerfileの`ENV`命令や`docker run`コマンドの`-e`オプションなどを使用して設定されます。

なお、`CMD`命令がDockerfile内に複数ある場合、最後の`CMD`命令だけが有効になります。また、`docker run`コマンドでコマンドを指定した場合、そのコマンドが`CMD`命令の内容を上書きします。

### sh -c は必要ですか？
Dockerfileの`CMD`命令や`ENTRYPOINT`命令では、シェル形式とexec形式の2つの形式が使用できます。

- シェル形式： `CMD command param1 param2`。この形式では、指定したコマンドは`/bin/sh -c`の下で実行され、環境変数の展開など、シェルの機能が利用できます。

- exec形式： `CMD ["executable","param1","param2"]`。この形式では、コマンドはシェルを経由せずに直接実行されます。

環境変数を含むコマンドをexec形式で実行する場合、環境変数の展開を行うために`sh -c`を使う必要があります。例えば、

```Dockerfile
CMD ["sh", "-c", "echo My database is $database"]
```

これは、シェル（`sh`）を起動し、そのシェルで`echo My database is $database`というコマンドを実行します。ここで`$database`は環境変数で、シェルの機能を通じて展開されます。

これに対して、次のように`sh -c`を省略した場合：

```Dockerfile
CMD ["echo", "My database is $database"]
```

これはシェルを介さずに`echo`コマンドを直接実行しますが、`$database`という環境変数は展開されません。したがって、実際には`My database is $database`という文字列がそのまま出力されます。

したがって、環境変数の展開を行いたい場合は、`sh -c`を使ってシェルを介してコマンドを実行する必要があります。

### -c の意味
`-c`オプションは、Unix系システムのシェル（例えば`sh`や`bash`など）で使用されるオプションです。`-c`オプションの後に指定した文字列をシェルコマンドとして実行します。

たとえば、`sh -c "echo hello"`というコマンドは、`sh`シェルを起動し、そのシェルで`echo hello`というコマンドを実行します。

Dockerfileの`CMD`命令や`ENTRYPOINT`命令でexec形式（`CMD ["executable","param1","param2"]`）を使用して環境変数を含むコマンドを実行する場合、環境変数の展開を行うために`sh -c`を使うことがあります。例えば、

```Dockerfile
CMD ["sh", "-c", "echo My database is $database"]
```

このコマンドは、`sh`シェルを起動し、そのシェルで`echo My database is $database`というコマンドを実行します。ここで`$database`は環境変数で、シェルの機能を通じて展開されます。

### なんの略？
`-c`オプションの`c`は "command" を意味します。つまり、`-c`は "command" の略です。

Unix系のシェルで、`-c`オプションを付けてシェルを起動すると、その後に続く文字列をシェルコマンドとして実行します。したがって、`-c`は "command" を意味し、その後に続く文字列が実行されるコマンドを示しています。

例えば、`sh -c "echo hello"`というコマンドは、`sh`シェルを起動し、そのシェルで`echo hello`というコマンドを実行します。ここで、`-c`の後に続く`"echo hello"`が実行されるコマンドを示しています。

## 