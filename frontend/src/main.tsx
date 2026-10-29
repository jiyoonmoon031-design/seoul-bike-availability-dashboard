import {
  QueryClient,
  QueryClientProvider,
} from '@tanstack/react-query'
import {
  StrictMode,
} from 'react'
import {
  createRoot,
} from 'react-dom/client'

import App from './App.tsx'
import './index.css'

const queryClient =
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
  })

async function enableMocking() {
  const useMsw =
    import.meta.env.DEV &&
    import.meta.env.VITE_USE_MSW !==
      'false'

  if (!useMsw) {
    return
  }

  const {
    worker,
  } = await import(
    './mocks/browser'
  )

  await worker.start({
    onUnhandledFrame: 'bypass',
  })
}

async function bootstrap() {
  await enableMocking()

  createRoot(
    document.getElementById(
      'root',
    )!,
  ).render(
    <StrictMode>
      <QueryClientProvider
        client={queryClient}
      >
        <App />
      </QueryClientProvider>
    </StrictMode>,
  )
}

void bootstrap()
