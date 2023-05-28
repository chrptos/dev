<template>
    <div>
        <span>子コンポーネント2の始まり</span>
        <slot name="child-component-2"></slot>
        <span>子コンポーネント2の終わり</span>
    </div>
</template>

<script setup lang="ts">
import ParentComponent from './ParentComponent.vue.js';
</script>

<style></style>