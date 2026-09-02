# CRLF-safe patching

Some projects' files are CRLF on disk (e.g. zng-app's Dart files, per project memory
`reference_dart_files_are_crlf_on_disk`). A naive LF-normalising write turns a one-line
change into a whole-file diff, and `sed -i` mangles CRLF outright.

On first encounter with a project that has CRLF files, or whenever an exact-string
replacement needs to survive a file's existing line endings, use the sanctioned helper
instead of hand-rolling a throwaway Python script:

```
python C:/Users/tecno/.claude/tools/patch-file.py <path> --replace <old-file> <new-file>
```

`--replace` is repeatable and takes files, not argv, so multi-line and quote-heavy
content survives shell quoting. A JSON payload on stdin (`--stdin-json`) is also
supported for callers that already have the content in memory.

It preserves the file's dominant line ending and UTF-8 BOM, refuses (rather than
silently normalises) a file with mixed endings, and refuses any `old` string that
does not match exactly once - see `tools/patch-file.py`'s own docstring for the
full contract. Self-tests: `tools/test_patch_file.py`.
