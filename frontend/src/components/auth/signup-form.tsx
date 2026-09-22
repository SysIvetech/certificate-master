'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { Loader2, Mail, Lock, Eye, EyeOff, User, GraduationCap, CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { AuthError, login, signup } from '@/lib/auth/auth-api'
import { useAuthStore } from '@/stores/auth-store'

// ivetech auth-service SignupRequest 규칙과 동일:
// 8~64자, 영문 대문자/소문자/숫자/특수문자 중 3종류 이상, 허용 문자만 사용
const SPECIAL_CHARS = '!@#$%^&*()_+-=[]{}|;\':",./<>?`~'
const ALLOWED_PASSWORD = /^[A-Za-z0-9!@#$%^&*()_+\-=[\]{}|;':",./<>?`~]+$/
const passwordClasses = (value: string) => [
  /[a-z]/.test(value),
  /[A-Z]/.test(value),
  /[0-9]/.test(value),
  value.split('').some((c) => SPECIAL_CHARS.includes(c)),
]

const signupSchema = z.object({
  fullName: z
    .string()
    .min(2, '이름은 최소 2자 이상이어야 합니다')
    .max(50, '이름은 50자 이하여야 합니다'),
  email: z.string().email('유효한 이메일을 입력해주세요'),
  password: z
    .string()
    .min(8, '비밀번호는 최소 8자 이상이어야 합니다')
    .max(64, '비밀번호는 64자 이하여야 합니다')
    .regex(ALLOWED_PASSWORD, '영문, 숫자, 특수문자만 사용할 수 있습니다')
    .refine((value) => passwordClasses(value).filter(Boolean).length >= 3, {
      message: '영문 대문자, 소문자, 숫자, 특수문자 중 3종류 이상 조합해주세요',
    }),
  confirmPassword: z.string(),
  agreeToTerms: z.boolean().refine((val) => val === true, {
    message: '이용약관에 동의해주세요',
  }),
}).refine((data) => data.password === data.confirmPassword, {
  message: '비밀번호가 일치하지 않습니다',
  path: ['confirmPassword'],
})

type SignupFormData = z.infer<typeof signupSchema>

export function SignupForm() {
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isSuccess, setIsSuccess] = useState(false)
  const router = useRouter()
  const { setUser } = useAuthStore()

  const form = useForm<SignupFormData>({
    resolver: zodResolver(signupSchema),
    defaultValues: {
      fullName: '',
      email: '',
      password: '',
      confirmPassword: '',
      agreeToTerms: false,
    },
  })

  const password = form.watch('password')

  const [hasLower, hasUpper, hasDigit, hasSpecial] = passwordClasses(password)
  const passwordRequirements = [
    { label: '8자 이상', met: password.length >= 8 },
    { label: '3종류 이상 조합', met: passwordClasses(password).filter(Boolean).length >= 3 },
    { label: '소문자', met: hasLower },
    { label: '대문자', met: hasUpper },
    { label: '숫자', met: hasDigit },
    { label: '특수문자', met: hasSpecial },
  ]

  const onSubmit = async (data: SignupFormData) => {
    setIsLoading(true)
    setError(null)

    try {
      await signup(data.email, data.password, data.fullName)
    } catch (err) {
      setError(err instanceof AuthError ? err.message : '회원가입 중 오류가 발생했습니다. 다시 시도해주세요.')
      setIsLoading(false)
      return
    }

    // 가입 직후 자동 로그인 (실패하면 완료 화면에서 로그인 페이지로 안내)
    try {
      const user = await login(data.email, data.password)
      if (user) {
        setUser(user)
        router.push('/')
        router.refresh()
        return
      }
      setIsSuccess(true)
    } catch {
      // 가입은 성공했으므로 완료 화면에서 로그인하도록 안내
      setIsSuccess(true)
    } finally {
      setIsLoading(false)
    }
  }

  if (isSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center py-12 px-4">
        {/* Background Effects */}
        <div className="absolute inset-0 -z-10 overflow-hidden">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl" />
        </div>

        <Card className="w-full max-w-md bg-card/80 border-border backdrop-blur-sm">
          <CardContent className="pt-10 pb-10 text-center">
            <div className="w-16 h-16 rounded-full bg-emerald-500/20 flex items-center justify-center mx-auto mb-6">
              <CheckCircle2 className="h-8 w-8 text-emerald-400" />
            </div>
            <h2 className="text-2xl font-bold text-foreground mb-2">
              가입이 완료되었습니다!
            </h2>
            <p className="text-muted-foreground mb-6">
              로그인하시면 모든 기능을 이용하실 수 있습니다.
            </p>
            <Button
              asChild
              className="bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-900 font-semibold"
            >
              <Link href="/login">로그인 하기</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center py-12 px-4">
      {/* Background Effects */}
      <div className="absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl" />
      </div>

      <Card className="w-full max-w-md bg-card/80 border-border backdrop-blur-sm">
        <CardHeader className="text-center pb-6">
          {/* Logo */}
          <Link href="/" className="inline-flex items-center justify-center gap-2 mb-6">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 to-cyan-500">
              <GraduationCap className="h-7 w-7 text-slate-900" />
            </div>
          </Link>
          <CardTitle className="text-2xl font-bold text-foreground">
            함께 시작해요!
          </CardTitle>
          <CardDescription className="text-muted-foreground">
            무료 계정을 만들고 자격증 준비를 시작하세요
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
              {/* Error Message */}
              {error && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                  {error}
                </div>
              )}

              {/* Full Name */}
              <FormField
                control={form.control}
                name="fullName"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-foreground/80">이름</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <User className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                        <Input
                          {...field}
                          type="text"
                          placeholder="홍길동"
                          className="pl-10 bg-muted/50 border-border text-foreground placeholder:text-muted-foreground focus-visible:border-emerald-500"
                        />
                      </div>
                    </FormControl>
                    <FormMessage className="text-red-400" />
                  </FormItem>
                )}
              />

              {/* Email */}
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-foreground/80">이메일</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                        <Input
                          {...field}
                          type="email"
                          placeholder="your@email.com"
                          className="pl-10 bg-muted/50 border-border text-foreground placeholder:text-muted-foreground focus-visible:border-emerald-500"
                        />
                      </div>
                    </FormControl>
                    <FormMessage className="text-red-400" />
                  </FormItem>
                )}
              />

              {/* Password */}
              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-foreground/80">비밀번호</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                        <Input
                          {...field}
                          type={showPassword ? 'text' : 'password'}
                          placeholder="••••••••"
                          className="pl-10 pr-10 bg-muted/50 border-border text-foreground placeholder:text-muted-foreground focus-visible:border-emerald-500"
                        />
                        <button
                          type="button"
                          aria-label={showPassword ? '비밀번호 숨기기' : '비밀번호 보기'}
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground/80"
                        >
                          {showPassword ? (
                            <EyeOff className="h-5 w-5" />
                          ) : (
                            <Eye className="h-5 w-5" />
                          )}
                        </button>
                      </div>
                    </FormControl>
                    {/* Password Requirements */}
                    {password.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-2">
                        {passwordRequirements.map((req) => (
                          <span
                            key={req.label}
                            className={`text-xs px-2 py-1 rounded ${
                              req.met
                                ? 'bg-emerald-500/20 text-emerald-400'
                                : 'bg-muted text-muted-foreground'
                            }`}
                          >
                            {req.label}
                          </span>
                        ))}
                      </div>
                    )}
                    <FormMessage className="text-red-400" />
                  </FormItem>
                )}
              />

              {/* Confirm Password */}
              <FormField
                control={form.control}
                name="confirmPassword"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-foreground/80">비밀번호 확인</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                        <Input
                          {...field}
                          type={showConfirmPassword ? 'text' : 'password'}
                          placeholder="••••••••"
                          className="pl-10 pr-10 bg-muted/50 border-border text-foreground placeholder:text-muted-foreground focus-visible:border-emerald-500"
                        />
                        <button
                          type="button"
                          aria-label={showConfirmPassword ? '비밀번호 숨기기' : '비밀번호 보기'}
                          onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground/80"
                        >
                          {showConfirmPassword ? (
                            <EyeOff className="h-5 w-5" />
                          ) : (
                            <Eye className="h-5 w-5" />
                          )}
                        </button>
                      </div>
                    </FormControl>
                    <FormMessage className="text-red-400" />
                  </FormItem>
                )}
              />

              {/* Terms Agreement */}
              <FormField
                control={form.control}
                name="agreeToTerms"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                    <FormControl>
                      <Checkbox
                        checked={field.value}
                        onCheckedChange={field.onChange}
                        className="border-slate-600 data-[state=checked]:bg-emerald-500 data-[state=checked]:border-emerald-500"
                      />
                    </FormControl>
                    <div className="space-y-1 leading-none">
                      <FormLabel className="text-sm text-muted-foreground font-normal">
                        <Link href="/terms" className="text-emerald-400 hover:underline">
                          이용약관
                        </Link>{' '}
                        및{' '}
                        <Link href="/privacy" className="text-emerald-400 hover:underline">
                          개인정보처리방침
                        </Link>
                        에 동의합니다
                      </FormLabel>
                      <FormMessage className="text-red-400" />
                    </div>
                  </FormItem>
                )}
              />

              {/* Submit Button */}
              <Button
                type="submit"
                disabled={isLoading}
                className="w-full bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-900 font-semibold hover:from-emerald-400 hover:to-cyan-400"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    가입 중\u2026
                  </>
                ) : (
                  '회원가입'
                )}
              </Button>

              {/* Login Link */}
              <p className="text-center text-sm text-muted-foreground">
                이미 계정이 있으신가요?{' '}
                <Link
                  href="/login"
                  className="text-emerald-400 hover:text-emerald-300 font-medium"
                >
                  로그인
                </Link>
              </p>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  )
}

