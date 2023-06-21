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


