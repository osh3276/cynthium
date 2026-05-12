```bash
#!/bin/bash
for f in *_final_adj_5mpp_surf.tif; do
    mv "$f" "${f/_final_adj_5mpp_surf.tif/_5mpp_surf.tif}"
done
```

