sp_io_stream_t sp_io_from_file(sp_str_t path, sp_io_mode_t mode) {
  int flags = 0;

  if ((mode & SP_IO_MODE_READ) && (mode & SP_IO_MODE_WRITE)) {
    flags = O_RDWR | O_CREAT;
  } else if ((mode & SP_IO_MODE_READ) && (mode & SP_IO_MODE_APPEND)) {
    flags = O_RDWR | O_CREAT | O_APPEND;
  } else if (mode & SP_IO_MODE_READ) {
    flags = O_RDONLY;
  } else if (mode & SP_IO_MODE_WRITE) {
    flags = O_WRONLY | O_CREAT | O_TRUNC;
  } else if (mode & SP_IO_MODE_APPEND) {
    flags = O_WRONLY | O_CREAT | O_APPEND;
  }
  const char* cpath = sp_str_to_cstr(path);
  int fd = open(cpath, flags, 0644);

  sp_io_stream_t stream = SP_ZERO_INITIALIZE();
  stream.callbacks = (sp_io_callbacks_t) {
    .size = sp_io_file_size,
    .seek = sp_io_file_seek,
    .read = sp_io_file_read,
    .write = sp_io_file_write,
    .close = sp_io_file_close,
  };
  stream.file.fd = fd;
  stream.file.close_mode = SP_IO_FILE_CLOSE_MODE_AUTO;

  if (fd < 0) {
    sp_err_set(SP_ERR_IO);
    return stream;
  }
  SP_ASSERT(sp_fs_is_target_regular_file(path));

  return stream;
}
