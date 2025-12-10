struct buffer {
    char *data;
    int len;
    int cap;
};

void buffer_init(struct buffer *b) {
    b->data = NULL;
    b->len = 0;
    b->cap = 0;
}

void buffer_push(struct buffer *b, char c) {
    if (b->len >= b->cap) {
        b->cap = b->cap ? b->cap * 2 : 16;
        b->data = realloc(b->data, b->cap);
    }
    b->data[b->len++] = c;
}

void buffer_free(struct buffer *b) {
    free(b->data);
    b->data = NULL;
    b->len = 0;
    b->cap = 0;
}
