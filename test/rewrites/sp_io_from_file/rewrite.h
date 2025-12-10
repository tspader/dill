sp_io_stream_t sp_io_from_file(sp_str_t path, sp_io_mode_t mode) {
  sp_io_stream_t stream = SP_ZERO_INITIALIZE();

  s32 flags = 0;
  s32 perms = S_IRUSR | S_IWUSR | S_IRGRP | S_IROTH;

  bool read_mode = (mode & SP_IO_MODE_READ) != 0;
  bool write_mode = (mode & SP_IO_MODE_WRITE) != 0;
  bool append_mode = (mode & SP_IO_MODE_APPEND) != 0;

  if (read_mode && write_mode) {
    flags = O_RDWR | O_CREAT;
  } else if (read_mode) {
    flags = O_RDONLY;
  } else if (append_mode) {
    flags = O_WRONLY | O_CREAT | O_APPEND;
  } else if (write_mode) {
    flags = O_WRONLY | O_CREAT | O_TRUNC;
  }

  c8* cpath = sp_str_to_cstr(path);
  s32 fd = open(cpath, flags, perms);
  sp_free(cpath);

  stream.file.fd = fd;
  stream.file.close_mode = SP_IO_FILE_CLOSE_MODE_AUTO;
  stream.callbacks = (sp_io_callbacks_t) {
    .size = sp_io_file_size,
    .seek = sp_io_file_seek,
    .read = sp_io_file_read,
    .write = sp_io_file_write,
    .close = sp_io_file_close,
  };

  return stream;
}
