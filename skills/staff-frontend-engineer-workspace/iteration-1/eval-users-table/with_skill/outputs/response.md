# Users Table Page

## 1. Architecture Overview

사용자 목록 테이블 페이지를 다음과 같은 구조로 설계한다.

```
features/
  users/
    types.ts                  # User 데이터 모델, Zod 스키마, API 응답 타입
    hooks/
      use-users.ts            # TanStack Query 기반 서버 상태 (검색, 페이지네이션, 필터)
      use-users-filter.ts     # URL 검색 파라미터 기반 필터 상태 관리
    components/
      users-page.tsx          # 페이지 레벨 컴포넌트 (ErrorBoundary + Suspense)
      users-table.tsx         # 테이블 본체 (shadcn/ui Table 활용)
      users-toolbar.tsx       # 검색 입력 + 역할 필터 드롭다운
      users-pagination.tsx    # 페이지네이션 컨트롤
      users-table-skeleton.tsx # 로딩 스켈레톤
```

**핵심 설계 결정:**

1. **URL 기반 상태 관리**: 검색어, 페이지, 필터를 URL search params로 관리한다. 이렇게 하면 브라우저 뒤로가기, 북마크, 링크 공유가 자연스럽게 동작한다. `nuqs` 같은 라이브러리 없이 Next.js의 `useSearchParams` + `useRouter`로 직접 구현한다.

2. **서버 사이드 페이지네이션**: 전체 데이터를 프론트에서 관리하지 않고, API에 `page`, `search`, `role` 파라미터를 전달하여 서버에서 필터링/페이지네이션한다. 대량 데이터에도 성능이 일정하다.

3. **관심사 분리**: 필터 상태(`use-users-filter`) → 데이터 페칭(`use-users`) → UI 렌더링(`users-table`)으로 단방향 데이터 흐름을 구성한다. 필터 로직이 바뀌어도 테이블 컴포넌트를 수정할 필요가 없다.

4. **Debounced Search**: 검색 입력 시 매 키 입력마다 API를 호출하지 않고, 300ms 디바운스를 적용한다.

```
[URL Search Params]
       |
       v
[useUsersFilter] -- search, page, role 파싱/직렬화
       |
       v
[useUsers] -- TanStack Query로 /api/users?search=...&page=...&role=... 호출
       |
       v
[UsersTable] -- 데이터가 있다고 가정하고 렌더링
       ^
       |
[UsersToolbar] -- 검색/필터 변경 시 URL 업데이트
[UsersPagination] -- 페이지 변경 시 URL 업데이트
```

---

## 2. Code Implementation

### Types / Schemas

```ts
// features/users/types.ts

import { z } from 'zod';

// --- Domain Schema ---

export const UserRoleSchema = z.enum(['admin', 'member', 'guest']);
export type UserRole = z.infer<typeof UserRoleSchema>;

export const USER_ROLE_LABELS: Record<UserRole, string> = {
  admin: '관리자',
  member: '멤버',
  guest: '게스트',
};

export const UserSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1),
  email: z.string().email(),
  role: UserRoleSchema,
  createdAt: z.string().datetime(),
});

export type User = z.infer<typeof UserSchema>;

// --- API Response Schema ---

export const UsersResponseSchema = z.object({
  data: z.array(UserSchema),
  pagination: z.object({
    page: z.number().int().positive(),
    pageSize: z.number().int().positive(),
    totalCount: z.number().int().nonnegative(),
    totalPages: z.number().int().nonnegative(),
  }),
});

export type UsersResponse = z.infer<typeof UsersResponseSchema>;

// --- Filter Params ---

export interface UsersFilterParams {
  search: string;
  page: number;
  role: UserRole | 'all';
}

export const DEFAULT_FILTER_PARAMS: UsersFilterParams = {
  search: '',
  page: 1,
  role: 'all',
};

export const PAGE_SIZE = 10;
```

### Hooks

```ts
// features/users/hooks/use-users-filter.ts

'use client';

import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { useCallback, useMemo, useTransition } from 'react';
import { type UsersFilterParams, type UserRole, DEFAULT_FILTER_PARAMS, UserRoleSchema } from '../types';

export function useUsersFilter() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();

  const filters: UsersFilterParams = useMemo(() => {
    const search = searchParams.get('search') ?? DEFAULT_FILTER_PARAMS.search;
    const page = Number(searchParams.get('page')) || DEFAULT_FILTER_PARAMS.page;
    const rawRole = searchParams.get('role') ?? 'all';
    const role = rawRole === 'all' ? 'all' : (UserRoleSchema.safeParse(rawRole).success ? rawRole as UserRole : 'all');

    return { search, page, role };
  }, [searchParams]);

  const setFilters = useCallback(
    (updates: Partial<UsersFilterParams>) => {
      const next = { ...filters, ...updates };

      // 검색어나 역할이 바뀌면 페이지를 1로 리셋
      if (updates.search !== undefined || updates.role !== undefined) {
        next.page = 1;
      }

      const params = new URLSearchParams();

      if (next.search) params.set('search', next.search);
      if (next.page > 1) params.set('page', String(next.page));
      if (next.role !== 'all') params.set('role', next.role);

      const queryString = params.toString();
      const url = queryString ? `${pathname}?${queryString}` : pathname;

      startTransition(() => {
        router.push(url, { scroll: false });
      });
    },
    [filters, pathname, router],
  );

  return { filters, setFilters, isPending };
}
```

```ts
// features/users/hooks/use-users.ts

import { useSuspenseQuery, queryOptions } from '@tanstack/react-query';
import { type UsersFilterParams, UsersResponseSchema, PAGE_SIZE } from '../types';

function buildUsersUrl(filters: UsersFilterParams): string {
  const params = new URLSearchParams();

  params.set('page', String(filters.page));
  params.set('pageSize', String(PAGE_SIZE));

  if (filters.search) {
    params.set('search', filters.search);
  }

  if (filters.role !== 'all') {
    params.set('role', filters.role);
  }

  return `/api/users?${params.toString()}`;
}

export function usersQueryOptions(filters: UsersFilterParams) {
  return queryOptions({
    queryKey: ['users', filters] as const,
    queryFn: async () => {
      const response = await fetch(buildUsersUrl(filters));

      if (!response.ok) {
        throw new Error(`사용자 목록 조회 실패: ${response.status}`);
      }

      const json: unknown = await response.json();
      return UsersResponseSchema.parse(json);
    },
    staleTime: 30_000,
    placeholderData: (previousData) => previousData,
  });
}

export function useUsers(filters: UsersFilterParams) {
  return useSuspenseQuery(usersQueryOptions(filters));
}
```

```ts
// features/users/hooks/use-debounced-value.ts

'use client';

import { useState, useEffect } from 'react';

export function useDebouncedValue<T>(value: T, delay: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}
```

### Components

```tsx
// features/users/components/users-page.tsx

'use client';

import { Suspense } from 'react';
import { ErrorBoundary } from 'react-error-boundary';
import { UsersTable } from './users-table';
import { UsersToolbar } from './users-toolbar';
import { UsersTableSkeleton } from './users-table-skeleton';
import { useUsersFilter } from '../hooks/use-users-filter';
import { Button } from '@/components/ui/button';
import { AlertCircle } from 'lucide-react';

function ErrorFallback({ error, resetErrorBoundary }: { error: Error; resetErrorBoundary: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 rounded-lg border border-destructive/50 bg-destructive/5 p-12">
      <AlertCircle className="h-10 w-10 text-destructive" />
      <div className="text-center">
        <p className="text-lg font-semibold">사용자 목록을 불러올 수 없습니다</p>
        <p className="mt-1 text-sm text-muted-foreground">{error.message}</p>
      </div>
      <Button variant="outline" onClick={resetErrorBoundary}>
        다시 시도
      </Button>
    </div>
  );
}

export function UsersPage() {
  const { filters, setFilters, isPending } = useUsersFilter();

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">사용자 관리</h1>
        <p className="text-sm text-muted-foreground">시스템에 등록된 사용자를 조회하고 관리합니다.</p>
      </div>

      <UsersToolbar filters={filters} onFiltersChange={setFilters} />

      <ErrorBoundary FallbackComponent={ErrorFallback}>
        <Suspense fallback={<UsersTableSkeleton />}>
          <UsersTable filters={filters} onPageChange={(page) => setFilters({ page })} isPending={isPending} />
        </Suspense>
      </ErrorBoundary>
    </div>
  );
}
```

```tsx
// features/users/components/users-toolbar.tsx

'use client';

import { useState, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Search } from 'lucide-react';
import { useDebouncedValue } from '../hooks/use-debounced-value';
import { type UsersFilterParams, type UserRole, USER_ROLE_LABELS } from '../types';

interface UsersToolbarProps {
  filters: UsersFilterParams;
  onFiltersChange: (updates: Partial<UsersFilterParams>) => void;
}

export function UsersToolbar({ filters, onFiltersChange }: UsersToolbarProps) {
  const [searchInput, setSearchInput] = useState(filters.search);
  const debouncedSearch = useDebouncedValue(searchInput);

  // URL에서 검색어가 바뀌면 입력값 동기화 (뒤로가기 등)
  useEffect(() => {
    setSearchInput(filters.search);
  }, [filters.search]);

  // 디바운스된 검색어가 변경되면 필터 업데이트
  useEffect(() => {
    if (debouncedSearch !== filters.search) {
      onFiltersChange({ search: debouncedSearch });
    }
  }, [debouncedSearch, filters.search, onFiltersChange]);

  const roleOptions: Array<{ value: UserRole | 'all'; label: string }> = [
    { value: 'all', label: '전체 역할' },
    ...Object.entries(USER_ROLE_LABELS).map(([value, label]) => ({
      value: value as UserRole,
      label,
    })),
  ];

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
      <div className="relative flex-1 sm:max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="이름 또는 이메일로 검색..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="pl-9"
        />
      </div>

      <Select
        value={filters.role}
        onValueChange={(value) => onFiltersChange({ role: value as UserRole | 'all' })}
      >
        <SelectTrigger className="w-full sm:w-[160px]">
          <SelectValue placeholder="역할 선택" />
        </SelectTrigger>
        <SelectContent>
          {roleOptions.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
```

```tsx
// features/users/components/users-table.tsx

'use client';

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { useUsers } from '../hooks/use-users';
import { UsersPagination } from './users-pagination';
import { type UsersFilterParams, type UserRole, USER_ROLE_LABELS } from '../types';

interface UsersTableProps {
  filters: UsersFilterParams;
  onPageChange: (page: number) => void;
  isPending: boolean;
}

const ROLE_BADGE_VARIANT: Record<UserRole, 'default' | 'secondary' | 'outline'> = {
  admin: 'default',
  member: 'secondary',
  guest: 'outline',
};

function formatDate(dateString: string): string {
  return new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(dateString));
}

export function UsersTable({ filters, onPageChange, isPending }: UsersTableProps) {
  const { data } = useUsers(filters);
  const { data: users, pagination } = data;

  if (users.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed p-12 text-center">
        <p className="text-lg font-medium text-muted-foreground">검색 결과가 없습니다</p>
        <p className="mt-1 text-sm text-muted-foreground">다른 검색어나 필터를 시도해 보세요.</p>
      </div>
    );
  }

  return (
    <div className={cn('space-y-4 transition-opacity', isPending && 'opacity-60')}>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[200px]">이름</TableHead>
              <TableHead>이메일</TableHead>
              <TableHead className="w-[100px]">역할</TableHead>
              <TableHead className="w-[120px]">가입일</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.map((user) => (
              <TableRow key={user.id}>
                <TableCell className="font-medium">{user.name}</TableCell>
                <TableCell className="text-muted-foreground">{user.email}</TableCell>
                <TableCell>
                  <Badge variant={ROLE_BADGE_VARIANT[user.role]}>
                    {USER_ROLE_LABELS[user.role]}
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">{formatDate(user.createdAt)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          총 {pagination.totalCount}명 중 {(pagination.page - 1) * pagination.pageSize + 1}-
          {Math.min(pagination.page * pagination.pageSize, pagination.totalCount)}명 표시
        </p>
        <UsersPagination
          currentPage={pagination.page}
          totalPages={pagination.totalPages}
          onPageChange={onPageChange}
        />
      </div>
    </div>
  );
}
```

```tsx
// features/users/components/users-pagination.tsx

'use client';

import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination';

interface UsersPaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

function getVisiblePages(current: number, total: number): Array<number | 'ellipsis'> {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }

  const pages: Array<number | 'ellipsis'> = [1];

  if (current > 3) {
    pages.push('ellipsis');
  }

  const start = Math.max(2, current - 1);
  const end = Math.min(total - 1, current + 1);

  for (let i = start; i <= end; i++) {
    pages.push(i);
  }

  if (current < total - 2) {
    pages.push('ellipsis');
  }

  if (total > 1) {
    pages.push(total);
  }

  return pages;
}

export function UsersPagination({ currentPage, totalPages, onPageChange }: UsersPaginationProps) {
  if (totalPages <= 1) return null;

  const visiblePages = getVisiblePages(currentPage, totalPages);

  return (
    <Pagination>
      <PaginationContent>
        <PaginationItem>
          <PaginationPrevious
            onClick={() => onPageChange(currentPage - 1)}
            aria-disabled={currentPage <= 1}
            className={currentPage <= 1 ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
          />
        </PaginationItem>

        {visiblePages.map((page, index) =>
          page === 'ellipsis' ? (
            <PaginationItem key={`ellipsis-${index}`}>
              <PaginationEllipsis />
            </PaginationItem>
          ) : (
            <PaginationItem key={page}>
              <PaginationLink
                isActive={page === currentPage}
                onClick={() => onPageChange(page)}
                className="cursor-pointer"
              >
                {page}
              </PaginationLink>
            </PaginationItem>
          ),
        )}

        <PaginationItem>
          <PaginationNext
            onClick={() => onPageChange(currentPage + 1)}
            aria-disabled={currentPage >= totalPages}
            className={currentPage >= totalPages ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
          />
        </PaginationItem>
      </PaginationContent>
    </Pagination>
  );
}
```

```tsx
// features/users/components/users-table-skeleton.tsx

import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

const SKELETON_ROWS = 10;

export function UsersTableSkeleton() {
  return (
    <div className="space-y-4">
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[200px]">이름</TableHead>
              <TableHead>이메일</TableHead>
              <TableHead className="w-[100px]">역할</TableHead>
              <TableHead className="w-[120px]">가입일</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {Array.from({ length: SKELETON_ROWS }, (_, i) => (
              <TableRow key={i}>
                <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                <TableCell><Skeleton className="h-4 w-40" /></TableCell>
                <TableCell><Skeleton className="h-5 w-14 rounded-full" /></TableCell>
                <TableCell><Skeleton className="h-4 w-20" /></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-8 w-64" />
      </div>
    </div>
  );
}
```

```tsx
// app/users/page.tsx

import { UsersPage } from '@/features/users/components/users-page';

export const metadata = {
  title: '사용자 관리',
  description: '시스템에 등록된 사용자를 조회하고 관리합니다.',
};

export default function Page() {
  return (
    <main className="container mx-auto py-8">
      <UsersPage />
    </main>
  );
}
```

---

## 3. Review Points

### 이 설계에서 특히 신경 쓴 부분

- **URL 상태 동기화**: 검색어, 페이지, 역할 필터가 모두 URL search params에 반영된다. 사용자가 브라우저 뒤로가기를 누르거나 URL을 공유해도 동일한 상태가 복원된다. `useTransition`을 활용하여 URL 업데이트 중 기존 UI가 유지되며, `isPending` 상태로 로딩 힌트(opacity 변경)를 제공한다.

- **Zod 런타임 검증**: API 응답을 `UsersResponseSchema.parse()`로 검증한다. 백엔드 스키마가 예고 없이 바뀌어도 프론트에서 즉시 파악 가능하다. 타입과 검증 로직이 한 곳(`types.ts`)에 있어 유지보수가 쉽다.

- **Debounced Search**: 검색 입력의 로컬 상태(`searchInput`)와 실제 필터 상태(`filters.search`)를 분리했다. 사용자는 즉각적인 입력 피드백을 받고, API 호출은 300ms 디바운스 후에만 발생한다.

- **Suspense + placeholderData**: `useSuspenseQuery`로 초기 로딩을 Suspense에 위임하고, `placeholderData: (previousData) => previousData`로 필터 변경 시 이전 데이터를 유지한다. 이렇게 하면 페이지 이동이나 필터 변경 시 테이블이 깜빡이지 않는다.

### 추후 요구사항 변경 시 수정 포인트

| 변경 사항 | 수정 파일 |
|---|---|
| 테이블 컬럼 추가 (예: 부서, 상태) | `types.ts`의 스키마 + `users-table.tsx`의 컬럼 |
| 정렬 기능 추가 | `types.ts`에 `sortBy`, `sortOrder` 추가 → `use-users-filter.ts`에서 파싱 → `use-users.ts`에서 API 파라미터 전달 → `users-table.tsx`의 헤더에 정렬 UI 추가 |
| 역할 외 다른 필터 추가 | `types.ts`에 필터 파라미터 추가 → `use-users-filter.ts`에서 파싱 → `users-toolbar.tsx`에 UI 추가 |
| 행 클릭 시 상세 페이지 이동 | `users-table.tsx`의 `TableRow`에 `onClick` + `router.push` 추가 |
| 서버 컴포넌트로 전환 (SSR) | `app/users/page.tsx`에서 직접 fetch + `HydrationBoundary`로 prefetch 데이터 전달 |

### 잠재적 성능 이슈 및 확장 고려 사항

- **대량 데이터**: 현재 서버 사이드 페이지네이션이므로 데이터 양에 관계없이 프론트 성능은 일정하다. 다만 `totalCount`가 수백만 건이면 DB 쿼리 최적화가 필요하다.

- **검색 UX**: 현재는 단순 디바운스이며, 빠른 타이핑 시 이전 요청이 완료되기 전에 새 요청이 나갈 수 있다. TanStack Query가 자동으로 최신 결과만 반영하므로 race condition 이슈는 없다.

- **React 19 `use` 활용**: 현재 `useSuspenseQuery`를 사용했지만, React 19의 `use(promise)` API를 직접 활용하는 방향으로도 전환 가능하다. 다만 TanStack Query의 캐싱/재시도/staleTime 등의 이점을 고려하면 현재 구조가 더 실용적이다.

- **접근성**: shadcn/ui 컴포넌트가 Radix UI 기반이므로 키보드 네비게이션과 스크린리더 지원이 기본 제공된다. 페이지네이션의 `aria-disabled` 속성도 명시적으로 처리했다.

- **테스트 전략**: 훅과 컴포넌트가 분리되어 있으므로, `use-users-filter`는 단위 테스트로 URL 파싱 로직을 검증하고, `UsersTable`은 MSW로 API를 모킹한 통합 테스트를 작성할 수 있다.
