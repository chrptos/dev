<script setup lang="ts">
import { reactive } from 'vue'

const url = 'https://www.amazon.co.jp/ref=nav_logo';

let item = reactive({
    name: 'Desk',
    price: 40000
})

const buy = (item: any) => {
    alert(item.name + '購入しました。');
}

</script>

<template>
    <div class="container">
        <h1>最近の支出</h1>
        <input type="text" v-model="item.name">
        <input type="text" v-model="item.price">
        <div class="payment">
            <label for="">{{ item.name }}</label>
            <label for="">{{ item.price }}円</label>
            <a v-bind:href="url">リンク</a>
            <button v-on:click="buy(item)">購入</button>
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