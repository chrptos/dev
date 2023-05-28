<template>
    <div>
        <slot></slot>
        <slot name="named-slot"></slot>
    </div>
</template>

<script setup lang="ts">
import ParentComponent from './ParentComponent.vue';
// propsを渡してあげれば実現できそうではあるが、htmlを生成するために全部の要素を渡すのってなる？
// スロットが主にレイアウトやマークアップを渡すのに対して、プロップスはデータや動作を渡している。
</script>

<style></style>