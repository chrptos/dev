<script setup lang="ts">
import { ref, defineProps, defineEmits } from 'vue';

type Tweet = {
    id: number,
    description: string,
}

type Props = {
    tweets: Tweet[]
}

const props = defineProps<Props>();

const emit = defineEmits(['post-tweet']);

const description = ref<string>('');

const postTweet = () => {
    emit('post-tweet', description.value);
}

</script>

<template>
    <div class="form-container">
        <div v-if="props.tweets.length <= 0">
            {{ 'No Tweets!!' }}
        </div>
        <div class="form-container">
            <input v-model="description" />
            <button @click="postTweet">ツイート</button>
        </div>
    </div>
</template>

<style scoped>
.form-container {
    display: flex;
    align-items: center;
    flex-direction: row;
    justify-content: space-around;
}
</style>