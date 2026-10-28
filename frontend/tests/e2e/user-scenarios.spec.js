import {
  expect,
  test,
} from '@playwright/test'

const scenarios = [
  ['세종대학교', '성수역'],
  ['건대입구역', '서울숲'],
  ['어린이대공원', '왕십리역'],
]

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

async function selectLocation(
  page,
  label,
  name,
) {
  const input = page.getByLabel(
    `${label} 검색어`,
  )
  const card = input.locator('..').locator('..')

  await input.fill(name)
  await card.getByRole('button', {
    name: '검색',
  }).click()
  await card.getByRole('button', {
    name: new RegExp(name),
  }).click()
}

for (const [origin, destination] of scenarios) {
  test(`${origin}에서 ${destination}까지 추천 흐름`, async ({
    page,
  }) => {
    await installKakaoMapStub(page)
    await page.goto('/')

    await selectLocation(
      page,
      '출발지',
      origin,
    )
    await selectLocation(
      page,
      '목적지',
      destination,
    )

    const originPanel = page.getByRole('article')
      .filter({
        has: page.getByRole('heading', {
          name: '출발 Top-3',
        }),
      })
    const destinationPanel = page.getByRole('article')
      .filter({
        has: page.getByRole('heading', {
          name: '도착 Top-3',
        }),
      })

    await expect(
      originPanel.locator('li'),
    ).toHaveCount(3)
    await expect(
      destinationPanel.locator('li'),
    ).toHaveCount(3)
    await expect(
      originPanel.locator(
        '.inventory-main span',
      ),
    ).toHaveCount(3)
    await expect(
      destinationPanel.locator(
        '.inventory-main span',
      ),
    ).toHaveCount(3)
    await expect(
      originPanel.locator(
        '.recommendation-reason',
      ),
    ).toHaveCount(3)
    await expect(
      destinationPanel.locator(
        '.recommendation-reason',
      ),
    ).toHaveCount(3)
    await expect(
      page.locator('.map-marker'),
    ).toHaveCount(8)
    await expect(
      page.getByRole('alert'),
    ).toHaveCount(0)
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
