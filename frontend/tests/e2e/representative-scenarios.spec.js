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
  test(`${origin}에서 ${destination}까지 전체 흐름`, async ({
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
