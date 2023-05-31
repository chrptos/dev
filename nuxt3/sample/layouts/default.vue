<template>
    <div class="container">
        <slot />
        <footer>&copy; footerをここに入力</footer>
    </div>
</template>

<style>
html {
    font-family: 'Monomaniac One', sans-serif;
}

.container {
    color: red;
}

footer {
    background-color: orange;
    text-align: center;
    color: white;
}
</style>