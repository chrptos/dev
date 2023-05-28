<template>
    <div>
        <ChildComponent>
            <h1>親からスロットへ要素を渡しています。</h1>
        </ChildComponent>
        <ChildComponent name="named-slot">
            <h1>親から名前付きスロットへ要素を渡しています。</h1>
        </ChildComponent>
    </div>
</template>

<script setup lang="ts">
import ChildComponent from './ChildComponent.vue';
</script>

<style></style>