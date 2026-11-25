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

test('긴 대여소명도 390px 화면에서 경로 카드 밖으로 넘치지 않는다', async ({
  page,
}) => {
  await page.setViewportSize({
    width: 390,
    height: 844,
  })
  await installKakaoMapStub(page)
  await page.goto('/')

  const originInput = page.getByLabel('출발지 검색어')
  await originInput.fill('세종대학교')
  await originInput.press('Enter')
  await page.getByRole('button', {
    name: /세종대학교/,
  }).first().click()

  const destinationInput = page.getByLabel('목적지 검색어')
  await destinationInput.fill('성수역')
  await destinationInput.press('Enter')
  await page.getByRole('button', {
    name: /성수역/,
  }).first().click()

  const firstRoute = page.getByRole('button', {
    name: /1위 경로 선택/,
  })
  await expect(firstRoute).toBeVisible()

  const bounds = await firstRoute.evaluate((element) => ({
    right: element.getBoundingClientRect().right,
    viewport: document.documentElement.clientWidth,
  }))

  expect(bounds.right).toBeLessThanOrEqual(bounds.viewport)
})
