void* sp_mem_arena_on_alloc(void* user_data, sp_mem_alloc_mode_t mode, u32 size, void* old_memory) {
  sp_mem_arena_t* arena = (sp_mem_arena_t*)user_data;

  switch (mode) {
    case SP_ALLOCATOR_MODE_ALLOC: {
      u32 aligned = sp_align_offset(arena->bytes_used, SP_MEM_ALIGNMENT);
      u32 total_bytes = aligned + sizeof(sp_arena_alloc_header_t) + size;

      if (total_bytes > arena->capacity) {
        u32 new_capacity = SP_MAX(arena->capacity * 2, total_bytes);
        arena->buffer = (u8*)sp_mem_os_realloc(arena->buffer, new_capacity);
        arena->capacity = new_capacity;
        SP_ASSERT(arena->buffer);
      }

      sp_arena_alloc_header_t* header = (sp_arena_alloc_header_t*)(arena->buffer + aligned);
      header->size = size;

      void* ptr = (u8*)header + sizeof(sp_arena_alloc_header_t);
      sp_mem_zero(ptr, size);
      arena->bytes_used = total_bytes;

      return ptr;
    }
    case SP_ALLOCATOR_MODE_RESIZE: {
      void* new_memory = sp_mem_arena_on_alloc(user_data, SP_ALLOCATOR_MODE_ALLOC, size, NULL);
      if (old_memory) {
        sp_arena_alloc_header_t* header = (sp_arena_alloc_header_t*)((u8*)old_memory - sizeof(sp_arena_alloc_header_t));
        sp_mem_move(old_memory, new_memory, SP_MIN(header->size, size));
      }
      return new_memory;
    }
    case SP_ALLOCATOR_MODE_FREE: {
      return SP_NULLPTR;
    }
  }

  SP_UNREACHABLE_RETURN(SP_NULLPTR);
}
