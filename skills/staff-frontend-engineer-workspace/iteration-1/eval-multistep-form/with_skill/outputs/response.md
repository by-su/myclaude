# Multi-Step Form (개인정보 / 주소 / 확인)

## 1. Architecture Overview

### 설계 의도

멀티스텝 폼은 "상태 관리"와 "유효성 검증"이 핵심이다. 이 구현에서는 다음 원칙을 따른다:

1. **Zustand로 스텝 간 상태 공유**: React의 리렌더링 트리 밖에서 폼 데이터를 관리하므로, 뒤로/앞으로 이동해도 데이터가 자연스럽게 유지된다. Context API 대비 보일러플레이트가 적고, 컴포넌트 외부에서도 상태에 접근 가능하다.

2. **Zod 스키마로 단계별 유효성 검증**: 각 단계마다 독립된 스키마를 정의하고, 전체 폼 스키마는 이들의 합성(merge)으로 구성한다. 런타임 검증과 TypeScript 타입 추론이 동시에 이뤄진다.

3. **관심사의 분리**: 폼 상태/로직은 `useMultiStepForm` 훅에, 각 단계의 UI는 독립된 스텝 컴포넌트에, 유효성 검증 규칙은 Zod 스키마에 분리한다.

### 컴포넌트 구조

```
features/
  multi-step-form/
    types.ts                    # Zod 스키마 & 타입 정의
    hooks/
      use-multi-step-form.ts    # Zustand 스토어 + 폼 로직
    components/
      multi-step-form.tsx       # 메인 컨테이너 (스텝 라우팅, 프로그레스 바)
      step-personal-info.tsx    # 1단계: 개인정보
      step-address.tsx          # 2단계: 주소
      step-confirmation.tsx     # 3단계: 확인
      form-navigation.tsx       # 이전/다음 버튼
      step-indicator.tsx        # 단계 표시 UI
```

### 데이터 흐름

```
[Zod Schema] ──정의──▶ [Types]
                           │
                      타입 추론
                           ▼
[Zustand Store] ◀──읽기/쓰기──▶ [useMultiStepForm Hook]
       │                                │
       │                          검증 로직 (Zod)
       │                                │
       ▼                                ▼
[Step Components] ◀──props──▶ [FormNavigation]
       │
       ▼
[StepIndicator] (현재 단계 시각화)
```

---

## 2. Code Implementation

### Types / Schemas

```ts
// features/multi-step-form/types.ts

import { z } from 'zod';

// ─── 1단계: 개인정보 스키마 ───
export const personalInfoSchema = z.object({
  name: z
    .string()
    .min(2, '이름은 2자 이상이어야 합니다')
    .max(50, '이름은 50자 이하여야 합니다'),
  email: z
    .string()
    .min(1, '이메일을 입력해주세요')
    .email('올바른 이메일 형식이 아닙니다'),
  phone: z
    .string()
    .min(1, '전화번호를 입력해주세요')
    .regex(
      /^01[016789]-?\d{3,4}-?\d{4}$/,
      '올바른 전화번호 형식이 아닙니다 (예: 010-1234-5678)'
    ),
});

// ─── 2단계: 주소 스키마 ───
export const addressSchema = z.object({
  postalCode: z
    .string()
    .min(1, '우편번호를 입력해주세요')
    .regex(/^\d{5}$/, '우편번호는 5자리 숫자입니다'),
  address: z
    .string()
    .min(1, '주소를 입력해주세요')
    .max(200, '주소는 200자 이하여야 합니다'),
  addressDetail: z
    .string()
    .max(100, '상세주소는 100자 이하여야 합니다')
    .optional()
    .default(''),
});

// ─── 전체 폼 스키마 (1단계 + 2단계 합성) ───
export const formSchema = personalInfoSchema.merge(addressSchema);

// ─── 타입 추론 ───
export type PersonalInfo = z.infer<typeof personalInfoSchema>;
export type Address = z.infer<typeof addressSchema>;
export type FormData = z.infer<typeof formSchema>;

// ─── 스텝 정의 ───
export const STEPS = [
  { id: 'personal-info', label: '개인정보' },
  { id: 'address', label: '주소' },
  { id: 'confirmation', label: '확인' },
] as const;

export type StepId = (typeof STEPS)[number]['id'];

// ─── 단계별 필드 에러 타입 ───
export type FieldErrors = Partial<Record<keyof FormData, string>>;
```

### Hooks

```ts
// features/multi-step-form/hooks/use-multi-step-form.ts

'use client';

import { create } from 'zustand';
import {
  type FieldErrors,
  type FormData,
  type StepId,
  STEPS,
  addressSchema,
  personalInfoSchema,
} from '../types';

interface MultiStepFormState {
  // 데이터
  formData: FormData;
  // 네비게이션
  currentStep: number;
  // 유효성 검증
  errors: FieldErrors;
  touchedSteps: Set<number>;

  // 액션
  updateField: <K extends keyof FormData>(key: K, value: FormData[K]) => void;
  setErrors: (errors: FieldErrors) => void;
  clearErrors: () => void;
  nextStep: () => boolean;
  prevStep: () => void;
  goToStep: (step: number) => void;
  reset: () => void;
}

const initialFormData: FormData = {
  name: '',
  email: '',
  phone: '',
  postalCode: '',
  address: '',
  addressDetail: '',
};

/**
 * 현재 단계에 대한 Zod 스키마 유효성 검증을 수행한다.
 * 성공 시 null, 실패 시 FieldErrors를 반환한다.
 */
function validateStep(step: number, data: FormData): FieldErrors | null {
  const schema = step === 0 ? personalInfoSchema : addressSchema;

  const result = schema.safeParse(data);
  if (result.success) return null;

  const errors: FieldErrors = {};
  for (const issue of result.error.issues) {
    const field = issue.path[0] as keyof FormData;
    // 첫 번째 에러만 표시
    if (!errors[field]) {
      errors[field] = issue.message;
    }
  }
  return errors;
}

export const useMultiStepFormStore = create<MultiStepFormState>((set, get) => ({
  formData: initialFormData,
  currentStep: 0,
  errors: {},
  touchedSteps: new Set<number>(),

  updateField: (key, value) => {
    set((state) => ({
      formData: { ...state.formData, [key]: value },
      // 필드 수정 시 해당 필드의 에러를 즉시 제거 (UX 개선)
      errors: { ...state.errors, [key]: undefined },
    }));
  },

  setErrors: (errors) => set({ errors }),
  clearErrors: () => set({ errors: {} }),

  nextStep: () => {
    const { currentStep, formData } = get();

    // 3단계(확인)에서는 다음 단계가 없음
    if (currentStep >= STEPS.length - 1) return false;

    // 확인 단계(2)로 가기 전까지만 유효성 검증
    if (currentStep < STEPS.length - 1) {
      const errors = validateStep(currentStep, formData);
      if (errors) {
        set({ errors });
        return false;
      }
    }

    set((state) => ({
      currentStep: state.currentStep + 1,
      errors: {},
      touchedSteps: new Set(state.touchedSteps).add(state.currentStep),
    }));
    return true;
  },

  prevStep: () => {
    set((state) => ({
      currentStep: Math.max(0, state.currentStep - 1),
      errors: {},
    }));
  },

  goToStep: (step) => {
    const { touchedSteps, currentStep } = get();
    // 이미 방문한 단계이거나 현재 단계 이전으로만 이동 가능
    if (touchedSteps.has(step) || step < currentStep) {
      set({ currentStep: step, errors: {} });
    }
  },

  reset: () =>
    set({
      formData: initialFormData,
      currentStep: 0,
      errors: {},
      touchedSteps: new Set(),
    }),
}));

/**
 * 컴포넌트에서 사용하는 커스텀 훅.
 * Zustand 스토어에서 필요한 값만 선택적으로 구독한다.
 */
export function useMultiStepForm() {
  const store = useMultiStepFormStore();

  const currentStepId = STEPS[store.currentStep]?.id as StepId;
  const isFirstStep = store.currentStep === 0;
  const isLastStep = store.currentStep === STEPS.length - 1;
  const progress = ((store.currentStep + 1) / STEPS.length) * 100;

  return {
    ...store,
    currentStepId,
    isFirstStep,
    isLastStep,
    progress,
    totalSteps: STEPS.length,
  };
}
```

### Components

```tsx
// features/multi-step-form/components/step-indicator.tsx

'use client';

import { cn } from '@/lib/utils';
import { Check } from 'lucide-react';

import { STEPS } from '../types';

interface StepIndicatorProps {
  currentStep: number;
  touchedSteps: Set<number>;
  onStepClick: (step: number) => void;
}

export function StepIndicator({
  currentStep,
  touchedSteps,
  onStepClick,
}: StepIndicatorProps) {
  return (
    <nav aria-label="진행 단계" className="mb-8">
      <ol className="flex items-center justify-between">
        {STEPS.map((step, index) => {
          const isCompleted = touchedSteps.has(index) && index < currentStep;
          const isCurrent = index === currentStep;
          const isClickable = touchedSteps.has(index) || index < currentStep;

          return (
            <li key={step.id} className="flex flex-1 items-center">
              <button
                type="button"
                onClick={() => onStepClick(index)}
                disabled={!isClickable}
                aria-current={isCurrent ? 'step' : undefined}
                className={cn(
                  'flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  isCurrent && 'bg-primary text-primary-foreground',
                  isCompleted &&
                    'text-primary hover:bg-primary/10 cursor-pointer',
                  !isCurrent &&
                    !isCompleted &&
                    'cursor-not-allowed text-muted-foreground'
                )}
              >
                <span
                  className={cn(
                    'flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 text-xs',
                    isCurrent && 'border-primary-foreground',
                    isCompleted && 'border-primary bg-primary text-primary-foreground',
                    !isCurrent && !isCompleted && 'border-muted-foreground'
                  )}
                >
                  {isCompleted ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    index + 1
                  )}
                </span>
                <span className="hidden sm:inline">{step.label}</span>
              </button>

              {index < STEPS.length - 1 && (
                <div
                  className={cn(
                    'mx-2 h-px flex-1',
                    isCompleted ? 'bg-primary' : 'bg-border'
                  )}
                  aria-hidden="true"
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
```

```tsx
// features/multi-step-form/components/form-navigation.tsx

'use client';

import { Button } from '@/components/ui/button';
import { ArrowLeft, ArrowRight, Send } from 'lucide-react';

interface FormNavigationProps {
  isFirstStep: boolean;
  isLastStep: boolean;
  onPrev: () => void;
  onNext: () => void;
  onSubmit: () => void;
}

export function FormNavigation({
  isFirstStep,
  isLastStep,
  onPrev,
  onNext,
  onSubmit,
}: FormNavigationProps) {
  return (
    <div className="mt-8 flex justify-between">
      <Button
        type="button"
        variant="outline"
        onClick={onPrev}
        disabled={isFirstStep}
        className="gap-2"
      >
        <ArrowLeft className="h-4 w-4" />
        이전
      </Button>

      {isLastStep ? (
        <Button type="button" onClick={onSubmit} className="gap-2">
          <Send className="h-4 w-4" />
          제출하기
        </Button>
      ) : (
        <Button type="button" onClick={onNext} className="gap-2">
          다음
          <ArrowRight className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}
```

```tsx
// features/multi-step-form/components/step-personal-info.tsx

'use client';

import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

import { cn } from '@/lib/utils';
import type { FieldErrors, FormData } from '../types';

interface StepPersonalInfoProps {
  formData: FormData;
  errors: FieldErrors;
  onFieldChange: <K extends keyof FormData>(key: K, value: FormData[K]) => void;
}

export function StepPersonalInfo({
  formData,
  errors,
  onFieldChange,
}: StepPersonalInfoProps) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">개인정보</h2>
        <p className="text-sm text-muted-foreground">
          기본적인 개인정보를 입력해주세요.
        </p>
      </div>

      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="name">
            이름 <span className="text-destructive">*</span>
          </Label>
          <Input
            id="name"
            value={formData.name}
            onChange={(e) => onFieldChange('name', e.target.value)}
            placeholder="홍길동"
            aria-invalid={!!errors.name}
            aria-describedby={errors.name ? 'name-error' : undefined}
            className={cn(errors.name && 'border-destructive')}
          />
          {errors.name && (
            <p id="name-error" className="text-sm text-destructive" role="alert">
              {errors.name}
            </p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="email">
            이메일 <span className="text-destructive">*</span>
          </Label>
          <Input
            id="email"
            type="email"
            value={formData.email}
            onChange={(e) => onFieldChange('email', e.target.value)}
            placeholder="example@email.com"
            aria-invalid={!!errors.email}
            aria-describedby={errors.email ? 'email-error' : undefined}
            className={cn(errors.email && 'border-destructive')}
          />
          {errors.email && (
            <p id="email-error" className="text-sm text-destructive" role="alert">
              {errors.email}
            </p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="phone">
            전화번호 <span className="text-destructive">*</span>
          </Label>
          <Input
            id="phone"
            type="tel"
            value={formData.phone}
            onChange={(e) => onFieldChange('phone', e.target.value)}
            placeholder="010-1234-5678"
            aria-invalid={!!errors.phone}
            aria-describedby={errors.phone ? 'phone-error' : undefined}
            className={cn(errors.phone && 'border-destructive')}
          />
          {errors.phone && (
            <p id="phone-error" className="text-sm text-destructive" role="alert">
              {errors.phone}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
```

```tsx
// features/multi-step-form/components/step-address.tsx

'use client';

import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

import { cn } from '@/lib/utils';
import type { FieldErrors, FormData } from '../types';

interface StepAddressProps {
  formData: FormData;
  errors: FieldErrors;
  onFieldChange: <K extends keyof FormData>(key: K, value: FormData[K]) => void;
}

export function StepAddress({
  formData,
  errors,
  onFieldChange,
}: StepAddressProps) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">주소</h2>
        <p className="text-sm text-muted-foreground">
          배송받으실 주소를 입력해주세요.
        </p>
      </div>

      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="postalCode">
            우편번호 <span className="text-destructive">*</span>
          </Label>
          <Input
            id="postalCode"
            value={formData.postalCode}
            onChange={(e) => onFieldChange('postalCode', e.target.value)}
            placeholder="12345"
            maxLength={5}
            aria-invalid={!!errors.postalCode}
            aria-describedby={errors.postalCode ? 'postalCode-error' : undefined}
            className={cn('max-w-32', errors.postalCode && 'border-destructive')}
          />
          {errors.postalCode && (
            <p
              id="postalCode-error"
              className="text-sm text-destructive"
              role="alert"
            >
              {errors.postalCode}
            </p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="address">
            주소 <span className="text-destructive">*</span>
          </Label>
          <Input
            id="address"
            value={formData.address}
            onChange={(e) => onFieldChange('address', e.target.value)}
            placeholder="서울특별시 강남구 테헤란로 123"
            aria-invalid={!!errors.address}
            aria-describedby={errors.address ? 'address-error' : undefined}
            className={cn(errors.address && 'border-destructive')}
          />
          {errors.address && (
            <p id="address-error" className="text-sm text-destructive" role="alert">
              {errors.address}
            </p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="addressDetail">상세주소</Label>
          <Input
            id="addressDetail"
            value={formData.addressDetail}
            onChange={(e) => onFieldChange('addressDetail', e.target.value)}
            placeholder="아파트 동/호수, 건물명 등"
            aria-invalid={!!errors.addressDetail}
            aria-describedby={
              errors.addressDetail ? 'addressDetail-error' : undefined
            }
            className={cn(errors.addressDetail && 'border-destructive')}
          />
          {errors.addressDetail && (
            <p
              id="addressDetail-error"
              className="text-sm text-destructive"
              role="alert"
            >
              {errors.addressDetail}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
```

```tsx
// features/multi-step-form/components/step-confirmation.tsx

'use client';

import { Separator } from '@/components/ui/separator';

import type { FormData } from '../types';

interface StepConfirmationProps {
  formData: FormData;
}

export function StepConfirmation({ formData }: StepConfirmationProps) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">입력 정보 확인</h2>
        <p className="text-sm text-muted-foreground">
          입력하신 정보를 확인해주세요. 수정이 필요하면 이전 단계로 돌아갈 수
          있습니다.
        </p>
      </div>

      <div className="rounded-lg border bg-card p-6 space-y-4">
        <section>
          <h3 className="text-sm font-medium text-muted-foreground">개인정보</h3>
          <dl className="mt-2 space-y-2">
            <ConfirmationRow label="이름" value={formData.name} />
            <ConfirmationRow label="이메일" value={formData.email} />
            <ConfirmationRow label="전화번호" value={formData.phone} />
          </dl>
        </section>

        <Separator />

        <section>
          <h3 className="text-sm font-medium text-muted-foreground">주소</h3>
          <dl className="mt-2 space-y-2">
            <ConfirmationRow label="우편번호" value={formData.postalCode} />
            <ConfirmationRow label="주소" value={formData.address} />
            {formData.addressDetail && (
              <ConfirmationRow label="상세주소" value={formData.addressDetail} />
            )}
          </dl>
        </section>
      </div>
    </div>
  );
}

function ConfirmationRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline gap-4">
      <dt className="w-20 shrink-0 text-sm text-muted-foreground">{label}</dt>
      <dd className="text-sm font-medium">{value}</dd>
    </div>
  );
}
```

```tsx
// features/multi-step-form/components/multi-step-form.tsx

'use client';

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';

import { useMultiStepForm } from '../hooks/use-multi-step-form';
import { formSchema } from '../types';
import { FormNavigation } from './form-navigation';
import { StepAddress } from './step-address';
import { StepConfirmation } from './step-confirmation';
import { StepIndicator } from './step-indicator';
import { StepPersonalInfo } from './step-personal-info';

export function MultiStepForm() {
  const {
    formData,
    currentStep,
    errors,
    touchedSteps,
    isFirstStep,
    isLastStep,
    updateField,
    nextStep,
    prevStep,
    goToStep,
    reset,
  } = useMultiStepForm();

  const { toast } = useToast();

  function handleSubmit() {
    // 최종 제출 전 전체 데이터 검증
    const result = formSchema.safeParse(formData);
    if (!result.success) {
      toast({
        variant: 'destructive',
        title: '입력 오류',
        description: '입력 정보를 다시 확인해주세요.',
      });
      return;
    }

    // TODO: 서버에 데이터 전송 (API 호출)
    console.log('Form submitted:', result.data);

    toast({
      title: '제출 완료',
      description: '정보가 성공적으로 제출되었습니다.',
    });

    reset();
  }

  return (
    <Card className="mx-auto w-full max-w-2xl">
      <CardHeader>
        <CardTitle>정보 입력</CardTitle>
        <CardDescription>
          아래 단계를 따라 정보를 입력해주세요.
        </CardDescription>
      </CardHeader>

      <CardContent>
        <StepIndicator
          currentStep={currentStep}
          touchedSteps={touchedSteps}
          onStepClick={goToStep}
        />

        {currentStep === 0 && (
          <StepPersonalInfo
            formData={formData}
            errors={errors}
            onFieldChange={updateField}
          />
        )}

        {currentStep === 1 && (
          <StepAddress
            formData={formData}
            errors={errors}
            onFieldChange={updateField}
          />
        )}

        {currentStep === 2 && (
          <StepConfirmation formData={formData} />
        )}

        <FormNavigation
          isFirstStep={isFirstStep}
          isLastStep={isLastStep}
          onPrev={prevStep}
          onNext={nextStep}
          onSubmit={handleSubmit}
        />
      </CardContent>
    </Card>
  );
}
```

### 사용 예시 (페이지에서)

```tsx
// app/form/page.tsx

import { MultiStepForm } from '@/features/multi-step-form/components/multi-step-form';

export default function FormPage() {
  return (
    <main className="container flex min-h-dvh items-center justify-center py-10">
      <MultiStepForm />
    </main>
  );
}
```

---

## 3. Review Points

### 이 설계에서 특히 신경 쓴 부분

1. **데이터 유지**: Zustand 스토어가 컴포넌트 라이프사이클 밖에서 상태를 관리하므로, 단계를 앞뒤로 이동해도 입력값이 절대 사라지지 않는다. `useState`로 각 스텝에 상태를 분산시켰다면, 컴포넌트 언마운트 시 데이터가 소실됐을 것이다.

2. **단계별 독립 검증**: Zod 스키마를 단계별로 분리(`personalInfoSchema`, `addressSchema`)하고, 제출 시에만 합성된 `formSchema`로 전체 검증한다. 이렇게 하면 새 단계를 추가할 때 해당 스키마만 정의하고 `formSchema`에 merge하면 된다.

3. **즉각적 에러 해제**: `updateField`에서 값이 변경되면 해당 필드의 에러를 즉시 제거한다. 사용자가 에러를 수정하는 도중에도 에러 메시지가 남아있으면 혼란을 줄 수 있기 때문이다.

4. **접근성(a11y)**: 모든 입력 필드에 `aria-invalid`, `aria-describedby`를 적용하고, 에러 메시지에는 `role="alert"`를, 스텝 인디케이터에는 `aria-current="step"`를 사용했다. 스크린 리더 사용자도 폼 상태를 파악할 수 있다.

5. **타입 안전성**: `updateField`의 제네릭 시그니처 `<K extends keyof FormData>(key: K, value: FormData[K])`가 키와 값의 타입 일치를 컴파일 타임에 보장한다. `updateField('name', 123)` 같은 실수는 컴파일 에러로 잡힌다.

### 추후 요구사항 변경 시 수정 포인트

| 변경 사항 | 수정 위치 |
|---|---|
| 새 단계 추가 (예: 결제 정보) | `types.ts`에 스키마 추가, `STEPS` 배열에 항목 추가, 새 스텝 컴포넌트 생성, `multi-step-form.tsx`에 렌더링 분기 추가 |
| 유효성 검증 규칙 변경 | `types.ts`의 Zod 스키마만 수정. UI 코드 변경 불필요 |
| 서버 제출 로직 추가 | `multi-step-form.tsx`의 `handleSubmit`에서 API 호출. TanStack Query의 `useMutation` 도입 권장 |
| 단계 간 조건부 이동 | `use-multi-step-form.ts`의 `nextStep`/`prevStep` 로직만 수정 |
| 폼 데이터 영속화 (새로고침 보존) | Zustand의 `persist` 미들웨어를 스토어에 추가 (`localStorage` 연동) |

### 잠재적 성능 이슈 및 확장 고려 사항

- **Zustand selector 최적화**: 현재 `useMultiStepForm`은 스토어 전체를 구독한다. 폼이 복잡해져 리렌더링이 문제가 되면, `useMultiStepFormStore((s) => s.formData.name)` 같이 세밀한 selector를 사용해 리렌더링 범위를 줄일 수 있다.

- **스텝 컴포넌트 동적 렌더링**: 현재 `currentStep === N` 조건 분기로 렌더링한다. 단계가 10개 이상으로 늘어나면, 스텝 컴포넌트를 배열/맵으로 관리하고 `steps[currentStep]`로 렌더링하는 패턴이 더 적합하다.

- **폼 라이브러리 도입 검토**: 필드가 20개 이상이거나, 복잡한 의존성 검증(필드 A의 값에 따라 필드 B의 검증 규칙이 바뀜)이 필요하면 `react-hook-form` + `@hookform/resolvers/zod` 조합 도입을 검토한다. 현재 구현은 직접 제어(controlled) 방식이라 필드가 많아지면 리렌더링 비용이 증가한다.

- **테스트 용이성**: 비즈니스 로직이 Zustand 스토어에 격리되어 있으므로, 컴포넌트 마운트 없이 스토어 단위 테스트가 가능하다. `validateStep` 함수도 순수 함수이므로 단위 테스트가 간단하다.
