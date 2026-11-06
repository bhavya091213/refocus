import zipfile, sys, collections
z = zipfile.ZipFile(sys.argv[1]); names = z.namelist()
print(len(names), "entries"); print("\n".join(names[:12]))
