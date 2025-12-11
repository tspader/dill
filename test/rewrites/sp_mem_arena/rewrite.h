void* sp_mem_arena_on_alloc(void* user_data, sp_mem_alloc_mode_t mode, u32 size, void* old_memory) {
  sp_mem_arena_t* arena = (sp_mem_arena_t*)user_data;

  switch (mode) {
    case SP_ALLOCATOR_MODE_ALLOC: {
      u32 header_size = sizeof(sp_arena_alloc_header_t);
      u32 total_size = header_size + size;

      // Calculate aligned position for user data (after header)
      u8* potential_header = arena->buffer + arena->bytes_used;
      u8* potential_user_data = potential_header + header_size;
      u8* aligned_user_data = (u8*)sp_align_up(potential_user_data, SP_MEM_ALIGNMENT);
      u8* aligned_header = aligned_user_data - header_size;

      u32 bytes_needed = (u32)(aligned_user_data - arena->buffer) + size;

      // Grow if necessary
      if (bytes_needed > arena->capacity) {
        sp_mem_arena_grow(arena, bytes_needed);
        // Recalculate after grow
        potential_header = arena->buffer + arena->bytes_used;
        potential_user_data = potential_header + header_size;
        aligned_user_data = (u8*)sp_align_up(potential_user_data, SP_MEM_ALIGNMENT);
        aligned_header = aligned_user_data - header_size;
      }

      // Write header
      sp_arena_alloc_header_t* header = (sp_arena_alloc_header_t*)aligned_header;
      header->size = size;

      // Zero the allocated memory
      sp_mem_zero(aligned_user_data, size);

      // Update bytes used
      arena->bytes_used = (u32)(aligned_user_data - arena->buffer) + size;

      return aligned_user_data;
    }
    case SP_ALLOCATOR_MODE_RESIZE: {
      if (!old_memory) {
        return sp_mem_arena_on_alloc(user_data, SP_ALLOCATOR_MODE_ALLOC, size, SP_NULLPTR);
      }

      // Get old allocation size from header
      sp_arena_alloc_header_t* old_header = ((sp_arena_alloc_header_t*)old_memory) - 1;
      u32 old_size = old_header->size;

      if (old_size >= size) {
        return old_memory;
      }

      // Allocate new block
      void* new_memory = sp_mem_arena_on_alloc(user_data, SP_ALLOCATOR_MODE_ALLOC, size, SP_NULLPTR);

      // Copy old data (only up to old_size, not new size)
      sp_mem_copy(old_memory, new_memory, old_size);

      return new_memory;
    }
    case SP_ALLOCATOR_MODE_FREE: {
      // Arena allocator doesn't support individual frees
      return SP_NULLPTR;
    }
  }

  return SP_NULLPTR;
}
