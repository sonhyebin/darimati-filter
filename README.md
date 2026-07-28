# DARIMATI Race Day Camera Filter

REXTREME (2026.08.01, 수원컨벤션센터) 현장용 카메라 필터. 단일 정적 페이지로 GitHub
Pages에서 서비스한다 → https://juno-5.github.io/darimati-filter/

참가자를 배경에서 분리(MediaPipe Selfie Segmentation)해서 브랜드 박스 프레임 **안에**
세우고, 기록·종목·이름을 얹어 저장/공유한다.

## 구조

```
index.html              앱 전체 (단일 파일)
frame-ribbon.jpg        RIBBON 프레임 배경 플레이트
frame-ribbon-fg.png     RIBBON 리본 — 인물보다 앞에 오는 전경 레이어
frame-sport.jpg         SPORT 프레임 배경 플레이트
assets-src/             원본 렌더 (PNG). 런타임에 쓰이지 않음
tools/build_frames.py   assets-src → 런타임 에셋 빌드
tools/preview_composite.py  카메라 없이 합성 결과 확인
```

## 합성 방식

프레임 아트에 **구멍을 뚫지 않는다.** 순서는 이렇다.

1. 프레임 플레이트를 배경으로 그린다 (아트가 100% 온전히 남는다)
2. 인물 누끼를 박스 내부 영역(`stage`)에 클립해서 위에 올린다
   - 가로 중앙 정렬, 위쪽 기준 정렬 → 머리가 살고 바닥선에서 잘린다
   - 좌우 가장자리는 페이드 → 팔이 벽선을 넘어가도 세로로 잘리지 않는다
   - 뒷벽에서 떠 보이게 그림자를 넣는다
3. 전경 레이어(RIBBON의 리본)를 인물 위에 올린다
4. 기록·종목·이름을 프레임별 좌표에 그린다

`FRAME_DEFS`의 모든 좌표는 **프레임 자체 너비/높이에 대한 비율**이다. 캔버스는 프레임의
원본 비율을 그대로 쓴다 (RIBBON 1055×1491, SPORT 1024×1536) — 9:16으로 강제하면 아트가
찌그러진다.

## 에셋 빌드

원본 렌더에는 `4:03:02`, `개인전`이 이미 박혀 있다. 빌드 스크립트가 그 부분을 지워서
런타임에 실제 값을 같은 자리에 그릴 수 있게 만든다.

```sh
python3 tools/build_frames.py     # 필요: pillow, numpy, scipy
```

지우는 영역·전경 추출 임계값은 `tools/build_frames.py`의 `FRAMES`에 있다. 원본 아트를
교체하면 좌표를 다시 재야 한다.

빌드 결과는 JPEG(플레이트는 알파가 필요 없음)라 2.9MB → 349KB로 줄어든다. 현장 LTE에서
첫 로딩이 걸리는 걸 막기 위한 것이니 PNG로 되돌리지 말 것.

## 확인

카메라 없이 합성을 보려면:

```sh
python3 tools/preview_composite.py            # 기록 입력된 상태
python3 tools/preview_composite.py --blank    # 기록 미입력 상태
```

브라우저에서는 `?demo=1`을 붙이면 카메라 대신 더미 실루엣으로 합성이 렌더된다.

```sh
python3 -m http.server 8000
open 'http://localhost:8000/?demo=1'
```

`preview_composite.py`는 `index.html`의 `FRAME_DEFS`/`SIDE_FADE`를 **복사해 두고 있다.**
한쪽을 고치면 다른 쪽도 맞춰야 한다.

## 알아둘 점

- 전면 카메라는 미러링해서 보여주고, 저장 이미지도 같은 방향이다 (포토부스 관례)
- 세그멘테이션 모델(`modelSelection: 0`)은 정사각 256×256 출력이라 세로 셀피에 유리하다.
  속도가 문제면 `1`(가로형, 144×256)로 낮출 수 있다
- 마스크 후처리는 256px 폭에서 돈다. 모델 출력이 그 이상이 아니라서 더 키워도 정보가
  늘지 않고 CPU만 쓴다
- MediaPipe CDN이 막히면 누끼 없이 원본 영상이 박스 안에 들어간 채로 계속 동작한다
- `ctx.filter`는 Safari 18부터라, 미지원 환경에서는 마스크 알파 램프를 넓혀서 대응한다
