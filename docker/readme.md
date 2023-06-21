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

## シェルとは
人間 -> シェル -> OS(カーネル)
シェルは人間が理解できる操作を機械語に翻訳して、OSに伝えてくれるし、逆に機械から人間の分かる言葉にしてくれたりする。

