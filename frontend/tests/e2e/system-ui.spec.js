import {
  expect,
  test,
} from '@playwright/test'

async function installKakaoMapStub(page) {
  await page.addInitScript(() => {
    class MapStub {
      constructor(container) {
        this.container = container
      }

      setBounds() {}
    }

    class CustomOverlayStub {
      constructor({
        map,
        content,
      }) {
        map.container.appendChild(content)
      }
    }

    window.kakao = {
      maps: {
        load: (callback) => callback(),
        Map: MapStub,
        LatLng: class {},
        LatLngBounds: class {
          extend() {}
        },
        CustomOverlay: CustomOverlayStub,
      },
    }
  })
}

test('짧은 검색어 오류를 안내한다', async ({
  page,
}) => {
  await installKakaoMapStub(page)
  await page.goto('/')

  await page.getByLabel('출발지 검색어')
    .fill('역')
  await page.getByLabel('출발지 검색어')
    .press('Enter')

  await expect(
    page.getByText(
      '검색어를 두 글자 이상 입력해 주세요.',
    ),
  ).toBeVisible()
})

test('운영자 탭의 우선순위 표를 표시한다', async ({
  page,
}) => {
  await installKakaoMapStub(page)
  await page.goto('/')
  await page.getByRole('button', {
    name: '운영자',
  }).click()

  await expect(
    page.getByRole('heading', {
      name: /따릉이 운영자 재배치/,
    }),
  ).toBeVisible()
  await expect(
    page.getByRole('heading', {
      name: '재배치 우선순위',
    }),
  ).toBeVisible()
  await expect(
    page.locator('tbody tr'),
  ).not.toHaveCount(0)
})

test('모바일 폭에서 이용자 화면이 넘치지 않는다', async ({
  page,
}) => {
  await page.setViewportSize({
    width: 390,
    height: 844,
  })
  await installKakaoMapStub(page)
  await page.goto('/')

  const sizes = await page.evaluate(() => ({
    clientWidth:
      document.documentElement.clientWidth,
    scrollWidth:
      document.documentElement.scrollWidth,
  }))

  expect(sizes.scrollWidth)
    .toBeLessThanOrEqual(sizes.clientWidth)
})
