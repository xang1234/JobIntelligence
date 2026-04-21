import { MoonIcon, SunIcon } from '@heroicons/react/24/outline'
import { IconButton } from '@/components/ui'
import { useTheme } from '@/contexts/ThemeContext'

export default function ThemeToggle() {
  const { theme, toggle } = useTheme()
  const isDark = theme === 'dark'
  return (
    <IconButton
      aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
      icon={isDark ? <SunIcon /> : <MoonIcon />}
      size="sm"
      variant="ghost"
      onClick={toggle}
    />
  )
}
