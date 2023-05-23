<script setup lang="ts">
const itemName1 = 'Desk';
const price1 = 400;
const url = 'https://www.amazon.co.jp/ref=nav_logo';
</script>

<template>
    <div class="container">
        <h1>最近の支出</h1>
        <div class="payment">
            <label for="">{{ itemName1 }}</label>
            <label for="">{{ price1 }}円</label>
            <a v-bind:href="url">リンク</a>
        </div>
    </div>
</template>

<style scoped>
label {
    font-size: 20px;
}

.container {
    display: flex;
    align-items: center;
    flex-direction: column;
}

.payment {
    display: flex;
    justify-content: space-between;
    height: 80px;
    width: 400px;
}
</style>