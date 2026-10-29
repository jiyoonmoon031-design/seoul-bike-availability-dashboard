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

test('출발·도착 Top-3 카드와 추천 이유를 표시한다', async ({
  page,
}) => {
  await installKakaoMapStub(page)
  await page.goto('/')

  await selectLocation(
    page,
    '출발지',
    '세종대학교',
  )
  await selectLocation(
    page,
    '목적지',
    '성수역',
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
})
