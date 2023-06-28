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
