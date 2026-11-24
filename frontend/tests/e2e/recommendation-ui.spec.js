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
        Polyline: class {
          setMap() {}
        },
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

test('출발과 도착을 묶은 Best 3 경로와 추천 이유를 표시한다', async ({
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

  const routePanel = page.getByRole('article')
    .filter({
      has: page.getByRole('heading', {
        name: 'Best 3 추천 경로',
      }),
    })

  await expect(
    routePanel.locator('.route-card'),
  ).toHaveCount(3)
  await expect(
    routePanel.locator(
      '.origin-availability',
    ),
  ).toHaveCount(3)
  await expect(
    routePanel.locator(
      '.destination-availability',
    ),
  ).toHaveCount(3)
  await expect(
    routePanel.locator(
      '.route-reason',
    ),
  ).toHaveCount(3)
  await expect(
    page.locator('.map-marker'),
  ).toHaveCount(8)

  await page.screenshot({
    path: '../reports/week13/browser-user-route.png',
    fullPage: true,
  })
})
