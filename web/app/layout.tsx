import { Inter, Crimson_Pro, JetBrains_Mono } from "next/font/google"

import "./globals.css"
import { ThemeProvider } from "@/components/theme-provider"
import { cn } from "@/lib/utils"
import { NavLinks } from "@/components/NavLinks"

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" })
const crimsonPro = Crimson_Pro({ subsets: ["latin"], variable: "--font-display" })
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
})

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={cn(
        "antialiased",
        inter.variable,
        crimsonPro.variable,
        jetbrainsMono.variable,
        "font-sans"
      )}
    >
      <body>
        <ThemeProvider>
          <nav className="sticky top-0 z-50 bg-background/70 backdrop-blur-xl">
            <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
              {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
              <a href="/" className="group flex items-center gap-2.5">
                {/* Logo mark — stacked tiles */}
                <span className="relative flex h-7 w-7 items-center justify-center">
                  <span className="absolute inset-0 rounded-[7px] bg-primary/15 transition-transform duration-300 group-hover:rotate-6" />
                  <span className="absolute inset-[3px] rounded-[5px] border border-primary/40 transition-transform duration-300 group-hover:-rotate-6" />
                  <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                </span>
                <span className="flex items-baseline gap-0.5">
                  <span className="font-display text-xl font-semibold tracking-tight">
                    Pixel
                  </span>
                  <span className="font-display text-xl font-semibold tracking-tight text-primary">
                    RAG
                  </span>
                </span>
              </a>
              <NavLinks />
            </div>
            {/* Gradient fade bottom border */}
            <div className="h-px bg-gradient-to-r from-transparent via-border to-transparent" />
          </nav>
          <main>{children}</main>
        </ThemeProvider>
      </body>
    </html>
  )
}
