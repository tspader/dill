struct vec2 {
    float x, y;
};

struct vec3 {
    float x, y, z;
};

float vec2_dot(struct vec2 a, struct vec2 b) {
    return a.x * b.x + a.y * b.y;
}

float vec2_len(struct vec2 v) {
    return sqrt(vec2_dot(v, v));
}

float vec3_dot(struct vec3 a, struct vec3 b) {
    return a.x * b.x + a.y * b.y + a.z * b.z;
}
