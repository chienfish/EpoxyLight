# EpoxyLight

## Documents
 - HackMD: https://hackmd.io/@6ZrLntymSnGyQ6g_vpxtuw/BJvIsebZgx
 - Figma: https://www.figma.com/design/0tL1Mnn6e3LShg20h2Gdof/EpoxyLight?node-id=0-1&t=MrNeagLOSFUJNlly-1 

---

## 終端機執行指令

#### 前端終端機
```
- cd EpoxyLight/frontend
- npm install
- npm start
```

#### 後端終端機
```
- cd EpoxyLight/backend
- pip install -r requirements.txt
- python backend.py
    - 這裡會出現 url，沒意外的話應該是'http://127.0.0.1:5000'
    - 若不是的話，到 EpoxyLight/frontend/package.json 中修改 proxy 的網址
```