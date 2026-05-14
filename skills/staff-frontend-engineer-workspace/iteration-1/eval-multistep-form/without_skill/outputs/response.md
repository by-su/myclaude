# 멀티스텝 폼 (Multi-Step Form)

React + TypeScript로 구현한 3단계 폼입니다. 각 단계마다 유효성 검증이 있고, 뒤로 가기해도 데이터가 유지됩니다.

## 구현 구조

```
src/
  components/
    MultiStepForm/
      MultiStepForm.tsx       # 메인 컨테이너
      StepPersonalInfo.tsx    # 1단계: 개인정보
      StepAddress.tsx         # 2단계: 주소
      StepConfirmation.tsx    # 3단계: 확인
      StepIndicator.tsx       # 단계 표시 UI
      useMultiStepForm.ts     # 폼 상태 관리 훅
      types.ts                # 타입 정의
      validation.ts           # 유효성 검증 로직
```

## 타입 정의 (`types.ts`)

```typescript
export interface PersonalInfo {
  name: string;
  email: string;
  phone: string;
}

export interface Address {
  zipCode: string;
  city: string;
  street: string;
  detail: string;
}

export interface FormData {
  personalInfo: PersonalInfo;
  address: Address;
}

export interface ValidationErrors {
  [key: string]: string;
}
```

## 유효성 검증 (`validation.ts`)

```typescript
import { PersonalInfo, Address, ValidationErrors } from "./types";

export function validatePersonalInfo(data: PersonalInfo): ValidationErrors {
  const errors: ValidationErrors = {};

  if (!data.name.trim()) {
    errors.name = "이름을 입력해주세요.";
  } else if (data.name.trim().length < 2) {
    errors.name = "이름은 2자 이상이어야 합니다.";
  }

  if (!data.email.trim()) {
    errors.email = "이메일을 입력해주세요.";
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email)) {
    errors.email = "올바른 이메일 형식이 아닙니다.";
  }

  if (!data.phone.trim()) {
    errors.phone = "전화번호를 입력해주세요.";
  } else if (!/^01[016789]-?\d{3,4}-?\d{4}$/.test(data.phone.replace(/-/g, ""))) {
    // 하이픈 제거 후 숫자만 검증
    if (!/^01[016789]\d{7,8}$/.test(data.phone.replace(/-/g, ""))) {
      errors.phone = "올바른 전화번호 형식이 아닙니다. (예: 010-1234-5678)";
    }
  }

  return errors;
}

export function validateAddress(data: Address): ValidationErrors {
  const errors: ValidationErrors = {};

  if (!data.zipCode.trim()) {
    errors.zipCode = "우편번호를 입력해주세요.";
  } else if (!/^\d{5}$/.test(data.zipCode.trim())) {
    errors.zipCode = "우편번호는 5자리 숫자여야 합니다.";
  }

  if (!data.city.trim()) {
    errors.city = "시/도를 입력해주세요.";
  }

  if (!data.street.trim()) {
    errors.street = "도로명 주소를 입력해주세요.";
  }

  if (!data.detail.trim()) {
    errors.detail = "상세 주소를 입력해주세요.";
  }

  return errors;
}
```

## 커스텀 훅 (`useMultiStepForm.ts`)

```typescript
import { useCallback, useState } from "react";
import { FormData, ValidationErrors } from "./types";
import { validatePersonalInfo, validateAddress } from "./validation";

const INITIAL_FORM_DATA: FormData = {
  personalInfo: { name: "", email: "", phone: "" },
  address: { zipCode: "", city: "", street: "", detail: "" },
};

const TOTAL_STEPS = 3;

export function useMultiStepForm() {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState<FormData>(INITIAL_FORM_DATA);
  const [errors, setErrors] = useState<ValidationErrors>({});
  const [isSubmitted, setIsSubmitted] = useState(false);

  const updatePersonalInfo = useCallback(
    (field: keyof FormData["personalInfo"], value: string) => {
      setFormData((prev) => ({
        ...prev,
        personalInfo: { ...prev.personalInfo, [field]: value },
      }));
      // 입력 시 해당 필드 에러 클리어
      setErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    },
    []
  );

  const updateAddress = useCallback(
    (field: keyof FormData["address"], value: string) => {
      setFormData((prev) => ({
        ...prev,
        address: { ...prev.address, [field]: value },
      }));
      setErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    },
    []
  );

  const validateCurrentStep = useCallback((): boolean => {
    let stepErrors: ValidationErrors = {};

    if (currentStep === 1) {
      stepErrors = validatePersonalInfo(formData.personalInfo);
    } else if (currentStep === 2) {
      stepErrors = validateAddress(formData.address);
    }

    setErrors(stepErrors);
    return Object.keys(stepErrors).length === 0;
  }, [currentStep, formData]);

  const goNext = useCallback(() => {
    if (!validateCurrentStep()) return;

    if (currentStep < TOTAL_STEPS) {
      setCurrentStep((prev) => prev + 1);
      setErrors({});
    }
  }, [currentStep, validateCurrentStep]);

  const goBack = useCallback(() => {
    if (currentStep > 1) {
      setCurrentStep((prev) => prev - 1);
      setErrors({});
    }
  }, [currentStep]);

  const goToStep = useCallback(
    (step: number) => {
      // 이전 단계로만 자유롭게 이동 가능 (데이터 유지)
      if (step < currentStep && step >= 1) {
        setCurrentStep(step);
        setErrors({});
      }
    },
    [currentStep]
  );

  const handleSubmit = useCallback(() => {
    console.log("폼 제출 데이터:", formData);
    setIsSubmitted(true);
  }, [formData]);

  const reset = useCallback(() => {
    setCurrentStep(1);
    setFormData(INITIAL_FORM_DATA);
    setErrors({});
    setIsSubmitted(false);
  }, []);

  return {
    currentStep,
    totalSteps: TOTAL_STEPS,
    formData,
    errors,
    isSubmitted,
    updatePersonalInfo,
    updateAddress,
    validateCurrentStep,
    goNext,
    goBack,
    goToStep,
    handleSubmit,
    reset,
  };
}
```

## 단계 표시 컴포넌트 (`StepIndicator.tsx`)

```tsx
interface StepIndicatorProps {
  currentStep: number;
  totalSteps: number;
  onStepClick: (step: number) => void;
}

const STEP_LABELS = ["개인정보", "주소", "확인"];

export function StepIndicator({
  currentStep,
  totalSteps,
  onStepClick,
}: StepIndicatorProps) {
  return (
    <div className="flex items-center justify-center mb-8">
      {Array.from({ length: totalSteps }, (_, i) => i + 1).map((step) => {
        const isActive = step === currentStep;
        const isCompleted = step < currentStep;
        const isClickable = step < currentStep;

        return (
          <div key={step} className="flex items-center">
            <button
              type="button"
              onClick={() => isClickable && onStepClick(step)}
              disabled={!isClickable}
              className={`
                flex items-center justify-center w-10 h-10 rounded-full
                text-sm font-semibold transition-colors duration-200
                ${isActive ? "bg-blue-600 text-white" : ""}
                ${isCompleted ? "bg-green-500 text-white cursor-pointer hover:bg-green-600" : ""}
                ${!isActive && !isCompleted ? "bg-gray-200 text-gray-500" : ""}
              `}
              aria-current={isActive ? "step" : undefined}
            >
              {isCompleted ? "✓" : step}
            </button>
            <span
              className={`ml-2 text-sm font-medium ${
                isActive ? "text-blue-600" : isCompleted ? "text-green-600" : "text-gray-400"
              }`}
            >
              {STEP_LABELS[step - 1]}
            </span>
            {step < totalSteps && (
              <div
                className={`w-12 h-0.5 mx-3 ${
                  isCompleted ? "bg-green-500" : "bg-gray-200"
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
```

## 1단계: 개인정보 (`StepPersonalInfo.tsx`)

```tsx
import { PersonalInfo, ValidationErrors } from "./types";

interface StepPersonalInfoProps {
  data: PersonalInfo;
  errors: ValidationErrors;
  onChange: (field: keyof PersonalInfo, value: string) => void;
}

export function StepPersonalInfo({ data, errors, onChange }: StepPersonalInfoProps) {
  return (
    <div className="space-y-5">
      <h2 className="text-xl font-bold text-gray-800 mb-4">개인정보 입력</h2>

      <div>
        <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
          이름 <span className="text-red-500">*</span>
        </label>
        <input
          id="name"
          type="text"
          value={data.name}
          onChange={(e) => onChange("name", e.target.value)}
          placeholder="홍길동"
          className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2
            ${errors.name ? "border-red-400 focus:ring-red-300" : "border-gray-300 focus:ring-blue-300"}`}
        />
        {errors.name && <p className="mt-1 text-sm text-red-500">{errors.name}</p>}
      </div>

      <div>
        <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
          이메일 <span className="text-red-500">*</span>
        </label>
        <input
          id="email"
          type="email"
          value={data.email}
          onChange={(e) => onChange("email", e.target.value)}
          placeholder="example@email.com"
          className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2
            ${errors.email ? "border-red-400 focus:ring-red-300" : "border-gray-300 focus:ring-blue-300"}`}
        />
        {errors.email && <p className="mt-1 text-sm text-red-500">{errors.email}</p>}
      </div>

      <div>
        <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-1">
          전화번호 <span className="text-red-500">*</span>
        </label>
        <input
          id="phone"
          type="tel"
          value={data.phone}
          onChange={(e) => onChange("phone", e.target.value)}
          placeholder="010-1234-5678"
          className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2
            ${errors.phone ? "border-red-400 focus:ring-red-300" : "border-gray-300 focus:ring-blue-300"}`}
        />
        {errors.phone && <p className="mt-1 text-sm text-red-500">{errors.phone}</p>}
      </div>
    </div>
  );
}
```

## 2단계: 주소 (`StepAddress.tsx`)

```tsx
import { Address, ValidationErrors } from "./types";

interface StepAddressProps {
  data: Address;
  errors: ValidationErrors;
  onChange: (field: keyof Address, value: string) => void;
}

export function StepAddress({ data, errors, onChange }: StepAddressProps) {
  return (
    <div className="space-y-5">
      <h2 className="text-xl font-bold text-gray-800 mb-4">주소 입력</h2>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="zipCode" className="block text-sm font-medium text-gray-700 mb-1">
            우편번호 <span className="text-red-500">*</span>
          </label>
          <input
            id="zipCode"
            type="text"
            value={data.zipCode}
            onChange={(e) => onChange("zipCode", e.target.value)}
            placeholder="12345"
            maxLength={5}
            className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2
              ${errors.zipCode ? "border-red-400 focus:ring-red-300" : "border-gray-300 focus:ring-blue-300"}`}
          />
          {errors.zipCode && <p className="mt-1 text-sm text-red-500">{errors.zipCode}</p>}
        </div>

        <div>
          <label htmlFor="city" className="block text-sm font-medium text-gray-700 mb-1">
            시/도 <span className="text-red-500">*</span>
          </label>
          <input
            id="city"
            type="text"
            value={data.city}
            onChange={(e) => onChange("city", e.target.value)}
            placeholder="서울특별시"
            className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2
              ${errors.city ? "border-red-400 focus:ring-red-300" : "border-gray-300 focus:ring-blue-300"}`}
          />
          {errors.city && <p className="mt-1 text-sm text-red-500">{errors.city}</p>}
        </div>
      </div>

      <div>
        <label htmlFor="street" className="block text-sm font-medium text-gray-700 mb-1">
          도로명 주소 <span className="text-red-500">*</span>
        </label>
        <input
          id="street"
          type="text"
          value={data.street}
          onChange={(e) => onChange("street", e.target.value)}
          placeholder="세종대로 110"
          className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2
            ${errors.street ? "border-red-400 focus:ring-red-300" : "border-gray-300 focus:ring-blue-300"}`}
        />
        {errors.street && <p className="mt-1 text-sm text-red-500">{errors.street}</p>}
      </div>

      <div>
        <label htmlFor="detail" className="block text-sm font-medium text-gray-700 mb-1">
          상세 주소 <span className="text-red-500">*</span>
        </label>
        <input
          id="detail"
          type="text"
          value={data.detail}
          onChange={(e) => onChange("detail", e.target.value)}
          placeholder="101동 202호"
          className={`w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2
            ${errors.detail ? "border-red-400 focus:ring-red-300" : "border-gray-300 focus:ring-blue-300"}`}
        />
        {errors.detail && <p className="mt-1 text-sm text-red-500">{errors.detail}</p>}
      </div>
    </div>
  );
}
```

## 3단계: 확인 (`StepConfirmation.tsx`)

```tsx
import { FormData } from "./types";

interface StepConfirmationProps {
  data: FormData;
  onEditStep: (step: number) => void;
}

export function StepConfirmation({ data, onEditStep }: StepConfirmationProps) {
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-gray-800 mb-4">입력 정보 확인</h2>

      <div className="bg-gray-50 rounded-lg p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-700">개인정보</h3>
          <button
            type="button"
            onClick={() => onEditStep(1)}
            className="text-sm text-blue-600 hover:text-blue-800 underline"
          >
            수정
          </button>
        </div>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
          <dt className="text-gray-500">이름</dt>
          <dd className="text-gray-800">{data.personalInfo.name}</dd>
          <dt className="text-gray-500">이메일</dt>
          <dd className="text-gray-800">{data.personalInfo.email}</dd>
          <dt className="text-gray-500">전화번호</dt>
          <dd className="text-gray-800">{data.personalInfo.phone}</dd>
        </dl>
      </div>

      <div className="bg-gray-50 rounded-lg p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-700">주소</h3>
          <button
            type="button"
            onClick={() => onEditStep(2)}
            className="text-sm text-blue-600 hover:text-blue-800 underline"
          >
            수정
          </button>
        </div>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
          <dt className="text-gray-500">우편번호</dt>
          <dd className="text-gray-800">{data.address.zipCode}</dd>
          <dt className="text-gray-500">시/도</dt>
          <dd className="text-gray-800">{data.address.city}</dd>
          <dt className="text-gray-500">도로명 주소</dt>
          <dd className="text-gray-800">{data.address.street}</dd>
          <dt className="text-gray-500">상세 주소</dt>
          <dd className="text-gray-800">{data.address.detail}</dd>
        </dl>
      </div>

      <p className="text-sm text-gray-500 text-center">
        위 정보가 맞으면 &quot;제출&quot; 버튼을 눌러주세요.
      </p>
    </div>
  );
}
```

## 메인 컨테이너 (`MultiStepForm.tsx`)

```tsx
import { useMultiStepForm } from "./useMultiStepForm";
import { StepIndicator } from "./StepIndicator";
import { StepPersonalInfo } from "./StepPersonalInfo";
import { StepAddress } from "./StepAddress";
import { StepConfirmation } from "./StepConfirmation";

export function MultiStepForm() {
  const {
    currentStep,
    totalSteps,
    formData,
    errors,
    isSubmitted,
    updatePersonalInfo,
    updateAddress,
    goNext,
    goBack,
    goToStep,
    handleSubmit,
    reset,
  } = useMultiStepForm();

  if (isSubmitted) {
    return (
      <div className="max-w-lg mx-auto mt-10 p-8 bg-white rounded-xl shadow-lg text-center">
        <div className="text-5xl mb-4">&#10003;</div>
        <h2 className="text-2xl font-bold text-gray-800 mb-2">제출 완료!</h2>
        <p className="text-gray-500 mb-6">
          입력하신 정보가 성공적으로 제출되었습니다.
        </p>
        <button
          type="button"
          onClick={reset}
          className="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          처음부터 다시 작성
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto mt-10 p-8 bg-white rounded-xl shadow-lg">
      <StepIndicator
        currentStep={currentStep}
        totalSteps={totalSteps}
        onStepClick={goToStep}
      />

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (currentStep === totalSteps) {
            handleSubmit();
          } else {
            goNext();
          }
        }}
      >
        {currentStep === 1 && (
          <StepPersonalInfo
            data={formData.personalInfo}
            errors={errors}
            onChange={updatePersonalInfo}
          />
        )}

        {currentStep === 2 && (
          <StepAddress
            data={formData.address}
            errors={errors}
            onChange={updateAddress}
          />
        )}

        {currentStep === 3 && (
          <StepConfirmation data={formData} onEditStep={goToStep} />
        )}

        <div className="flex justify-between mt-8">
          <button
            type="button"
            onClick={goBack}
            disabled={currentStep === 1}
            className={`px-6 py-2.5 rounded-lg font-medium transition-colors
              ${
                currentStep === 1
                  ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                  : "bg-gray-200 text-gray-700 hover:bg-gray-300"
              }`}
          >
            이전
          </button>

          <button
            type="submit"
            className={`px-6 py-2.5 rounded-lg font-medium text-white transition-colors
              ${
                currentStep === totalSteps
                  ? "bg-green-600 hover:bg-green-700"
                  : "bg-blue-600 hover:bg-blue-700"
              }`}
          >
            {currentStep === totalSteps ? "제출" : "다음"}
          </button>
        </div>
      </form>
    </div>
  );
}
```

## 사용 예시 (`App.tsx`)

```tsx
import { MultiStepForm } from "./components/MultiStepForm/MultiStepForm";

function App() {
  return (
    <div className="min-h-screen bg-gray-100 py-10">
      <MultiStepForm />
    </div>
  );
}

export default App;
```

## 핵심 설계 포인트

### 1. 데이터 유지 (뒤로 가기)
- `useMultiStepForm` 훅에서 `formData` 상태를 단일 객체로 관리합니다.
- 단계 이동 시 `currentStep`만 변경하고, `formData`는 그대로 유지합니다.
- 따라서 뒤로 가기 후에도 이전에 입력한 데이터가 모두 남아 있습니다.

### 2. 단계별 유효성 검증
- **1단계**: 이름(2자 이상), 이메일(정규식), 전화번호(한국 휴대폰 형식) 검증
- **2단계**: 우편번호(5자리 숫자), 시/도, 도로명 주소, 상세 주소 필수 입력 검증
- **3단계**: 확인 화면이므로 별도 검증 없음 (이미 1, 2단계에서 완료)
- `goNext()` 호출 시 현재 단계 검증을 통과해야만 다음 단계로 이동합니다.

### 3. 입력 중 에러 클리어
- 사용자가 필드를 수정하면 해당 필드의 에러 메시지가 즉시 사라집니다.
- 이를 통해 "에러 확인 -> 수정 -> 에러 사라짐"의 자연스러운 UX를 제공합니다.

### 4. 단계 인디케이터 네비게이션
- 완료된 단계(초록색 체크)를 클릭하면 해당 단계로 바로 이동할 수 있습니다.
- 아직 도달하지 않은 단계로는 클릭으로 이동할 수 없습니다 (검증 우회 방지).

### 5. 확인 단계에서 수정
- 3단계 확인 화면에서 각 섹션 옆의 "수정" 버튼을 누르면 해당 단계로 돌아갈 수 있습니다.
- 수정 후 다시 다음 단계로 진행하면 됩니다.
