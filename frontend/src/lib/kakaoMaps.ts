export type KakaoLatLng = {
  getLat: () => number
  getLng: () => number
}

export type KakaoLatLngBounds = {
  extend: (position: KakaoLatLng) => void
}

export type KakaoMapInstance = {
  setBounds: (
    bounds: KakaoLatLngBounds,
  ) => void
  relayout: () => void
}

export type KakaoOverlay = {
  setMap: (
    map: KakaoMapInstance | null,
  ) => void
}

export type KakaoMapsApi = {
  load: (
    callback: () => void,
  ) => void

  LatLng: new (
    lat: number,
    lon: number,
  ) => KakaoLatLng

  LatLngBounds:
    new () => KakaoLatLngBounds

  Map: new (
    container: HTMLElement,
    options: {
      center: KakaoLatLng
      level?: number
    },
  ) => KakaoMapInstance

  CustomOverlay: new (
    options: {
      map?: KakaoMapInstance
      position: KakaoLatLng
      content: string | HTMLElement
      clickable?: boolean
      xAnchor?: number
      yAnchor?: number
      zIndex?: number
    },
  ) => KakaoOverlay

  Polyline: new (
    options: {
      map?: KakaoMapInstance
      path: KakaoLatLng[]
      strokeWeight?: number
      strokeColor?: string
      strokeOpacity?: number
      strokeStyle?: string
      endArrow?: boolean
      zIndex?: number
    },
  ) => KakaoOverlay
}

type KakaoGlobal = {
  maps: KakaoMapsApi
}

type KakaoWindow = Window & {
  kakao?: KakaoGlobal
}

let sdkPromise:
  Promise<KakaoMapsApi> | null =
    null

function getKakaoWindow() {
  return window as KakaoWindow
}

export function loadKakaoMaps():
  Promise<KakaoMapsApi> {
  if (sdkPromise) {
    return sdkPromise
  }

  sdkPromise =
    new Promise(
      (resolve, reject) => {
        const appKey =
          import.meta.env
            .VITE_KAKAO_JAVASCRIPT_KEY

        if (!appKey) {
          reject(
            new Error(
              'VITE_KAKAO_JAVASCRIPT_KEY is missing',
            ),
          )
          return
        }

        const kakaoWindow =
          getKakaoWindow()

        const finishLoading =
          () => {
            const maps =
              getKakaoWindow()
                .kakao?.maps

            if (!maps) {
              reject(
                new Error(
                  'Kakao Maps SDK did not initialize',
                ),
              )
              return
            }

            maps.load(() =>
              resolve(maps),
            )
          }

        if (
          kakaoWindow.kakao?.maps
        ) {
          finishLoading()
          return
        }

        const existing =
          document.querySelector<
            HTMLScriptElement
          >(
            '#kakao-maps-sdk',
          )

        if (existing) {
          existing.addEventListener(
            'load',
            finishLoading,
            { once: true },
          )

          existing.addEventListener(
            'error',
            () =>
              reject(
                new Error(
                  'Failed to load Kakao Maps SDK',
                ),
              ),
            { once: true },
          )

          return
        }

        const script =
          document.createElement(
            'script',
          )

        script.id =
          'kakao-maps-sdk'

        script.async = true

        script.src =
          'https://dapi.kakao.com/v2/maps/sdk.js' +
          `?appkey=${encodeURIComponent(appKey)}` +
          '&autoload=false'

        script.addEventListener(
          'load',
          finishLoading,
          { once: true },
        )

        script.addEventListener(
          'error',
          () =>
            reject(
              new Error(
                'Failed to load Kakao Maps SDK',
              ),
            ),
          { once: true },
        )

        document.head.appendChild(
          script,
        )
      },
    )

  return sdkPromise
}
