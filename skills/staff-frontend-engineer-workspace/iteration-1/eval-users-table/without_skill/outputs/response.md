# 사용자 목록 테이블 페이지

검색, 페이지네이션, 역할별 필터링 기능이 포함된 사용자 목록 테이블 페이지입니다.

## 타입 정의

```typescript
// types/user.ts

export type Role = "admin" | "editor" | "viewer";

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  createdAt: string;
}

export interface UsersResponse {
  users: User[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface UsersQueryParams {
  page: number;
  pageSize: number;
  search?: string;
  role?: Role | "all";
}
```

## 커스텀 훅

```typescript
// hooks/use-users.ts

import { useState, useEffect, useCallback } from "react";
import type { User, UsersResponse, UsersQueryParams, Role } from "@/types/user";

interface UseUsersReturn {
  users: User[];
  total: number;
  totalPages: number;
  page: number;
  pageSize: number;
  search: string;
  role: Role | "all";
  isLoading: boolean;
  error: string | null;
  setPage: (page: number) => void;
  setSearch: (search: string) => void;
  setRole: (role: Role | "all") => void;
}

export function useUsers(initialPageSize = 10): UseUsersReturn {
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(initialPageSize);
  const [search, setSearchValue] = useState("");
  const [role, setRoleValue] = useState<Role | "all">("all");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    const params = new URLSearchParams({
      page: String(page),
      pageSize: String(pageSize),
    });

    if (search) params.set("search", search);
    if (role !== "all") params.set("role", role);

    try {
      const response = await fetch(`/api/users?${params.toString()}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch users: ${response.status}`);
      }

      const data: UsersResponse = await response.json();
      setUsers(data.users);
      setTotal(data.total);
      setTotalPages(data.totalPages);
    } catch (err) {
      const message = err instanceof Error ? err.message : "An error occurred";
      setError(message);
      setUsers([]);
      setTotal(0);
      setTotalPages(0);
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize, search, role]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const setSearch = useCallback((value: string) => {
    setSearchValue(value);
    setPage(1);
  }, []);

  const setRole = useCallback((value: Role | "all") => {
    setRoleValue(value);
    setPage(1);
  }, []);

  return {
    users,
    total,
    totalPages,
    page,
    pageSize,
    search,
    role,
    isLoading,
    error,
    setPage,
    setSearch,
    setRole,
  };
}
```

## 디바운스 훅

```typescript
// hooks/use-debounce.ts

import { useState, useEffect } from "react";

export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}
```

## 컴포넌트 구현

### 검색 입력 컴포넌트

```tsx
// components/users/search-input.tsx

"use client";

import { useState, useEffect } from "react";
import { useDebounce } from "@/hooks/use-debounce";

interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export function SearchInput({
  value,
  onChange,
  placeholder = "이름 또는 이메일로 검색...",
}: SearchInputProps) {
  const [localValue, setLocalValue] = useState(value);
  const debouncedValue = useDebounce(localValue, 300);

  useEffect(() => {
    onChange(debouncedValue);
  }, [debouncedValue, onChange]);

  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  return (
    <div className="relative">
      <svg
        className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth={1.5}
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
        />
      </svg>
      <input
        type="text"
        value={localValue}
        onChange={(e) => setLocalValue(e.target.value)}
        placeholder={placeholder}
        className="h-10 w-full rounded-md border border-input bg-background px-3 py-2 pl-10 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      />
    </div>
  );
}
```

### 역할 필터 컴포넌트

```tsx
// components/users/role-filter.tsx

"use client";

import type { Role } from "@/types/user";

interface RoleFilterProps {
  value: Role | "all";
  onChange: (value: Role | "all") => void;
}

const ROLE_OPTIONS: { value: Role | "all"; label: string }[] = [
  { value: "all", label: "전체" },
  { value: "admin", label: "관리자" },
  { value: "editor", label: "편집자" },
  { value: "viewer", label: "뷰어" },
];

export function RoleFilter({ value, onChange }: RoleFilterProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as Role | "all")}
      className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
    >
      {ROLE_OPTIONS.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}
```

### 페이지네이션 컴포넌트

```tsx
// components/users/pagination.tsx

"use client";

interface PaginationProps {
  page: number;
  totalPages: number;
  total: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}

export function Pagination({
  page,
  totalPages,
  total,
  pageSize,
  onPageChange,
}: PaginationProps) {
  const startItem = (page - 1) * pageSize + 1;
  const endItem = Math.min(page * pageSize, total);

  const getVisiblePages = (): (number | "ellipsis")[] => {
    if (totalPages <= 7) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }

    const pages: (number | "ellipsis")[] = [1];

    if (page > 3) {
      pages.push("ellipsis");
    }

    const start = Math.max(2, page - 1);
    const end = Math.min(totalPages - 1, page + 1);

    for (let i = start; i <= end; i++) {
      pages.push(i);
    }

    if (page < totalPages - 2) {
      pages.push("ellipsis");
    }

    pages.push(totalPages);
    return pages;
  };

  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-between">
      <p className="text-sm text-muted-foreground">
        전체 {total}건 중 {startItem}-{endItem}
      </p>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-input bg-background text-sm font-medium hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-50"
          aria-label="이전 페이지"
        >
          &lt;
        </button>

        {getVisiblePages().map((p, i) =>
          p === "ellipsis" ? (
            <span key={`ellipsis-${i}`} className="px-2 text-muted-foreground">
              ...
            </span>
          ) : (
            <button
              key={p}
              onClick={() => onPageChange(p)}
              className={`inline-flex h-9 w-9 items-center justify-center rounded-md text-sm font-medium ${
                p === page
                  ? "bg-primary text-primary-foreground"
                  : "border border-input bg-background hover:bg-accent hover:text-accent-foreground"
              }`}
            >
              {p}
            </button>
          )
        )}

        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-input bg-background text-sm font-medium hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-50"
          aria-label="다음 페이지"
        >
          &gt;
        </button>
      </div>
    </div>
  );
}
```

### 역할 뱃지 컴포넌트

```tsx
// components/users/role-badge.tsx

import type { Role } from "@/types/user";

const ROLE_CONFIG: Record<Role, { label: string; className: string }> = {
  admin: {
    label: "관리자",
    className: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  },
  editor: {
    label: "편집자",
    className:
      "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  },
  viewer: {
    label: "뷰어",
    className:
      "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200",
  },
};

export function RoleBadge({ role }: { role: Role }) {
  const config = ROLE_CONFIG[role];

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${config.className}`}
    >
      {config.label}
    </span>
  );
}
```

### 사용자 테이블 컴포넌트

```tsx
// components/users/users-table.tsx

"use client";

import type { User } from "@/types/user";
import { RoleBadge } from "./role-badge";

interface UsersTableProps {
  users: User[];
  isLoading: boolean;
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

function TableSkeleton() {
  return (
    <>
      {Array.from({ length: 5 }).map((_, i) => (
        <tr key={i} className="animate-pulse">
          <td className="px-6 py-4">
            <div className="h-4 w-24 rounded bg-muted" />
          </td>
          <td className="px-6 py-4">
            <div className="h-4 w-40 rounded bg-muted" />
          </td>
          <td className="px-6 py-4">
            <div className="h-5 w-16 rounded-full bg-muted" />
          </td>
          <td className="px-6 py-4">
            <div className="h-4 w-24 rounded bg-muted" />
          </td>
        </tr>
      ))}
    </>
  );
}

export function UsersTable({ users, isLoading }: UsersTableProps) {
  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead className="border-b bg-muted/50">
          <tr>
            <th className="px-6 py-3 text-left font-medium text-muted-foreground">
              이름
            </th>
            <th className="px-6 py-3 text-left font-medium text-muted-foreground">
              이메일
            </th>
            <th className="px-6 py-3 text-left font-medium text-muted-foreground">
              역할
            </th>
            <th className="px-6 py-3 text-left font-medium text-muted-foreground">
              가입일
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {isLoading ? (
            <TableSkeleton />
          ) : users.length === 0 ? (
            <tr>
              <td
                colSpan={4}
                className="px-6 py-12 text-center text-muted-foreground"
              >
                검색 결과가 없습니다.
              </td>
            </tr>
          ) : (
            users.map((user) => (
              <tr
                key={user.id}
                className="transition-colors hover:bg-muted/50"
              >
                <td className="px-6 py-4 font-medium">{user.name}</td>
                <td className="px-6 py-4 text-muted-foreground">
                  {user.email}
                </td>
                <td className="px-6 py-4">
                  <RoleBadge role={user.role} />
                </td>
                <td className="px-6 py-4 text-muted-foreground">
                  {formatDate(user.createdAt)}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
```

### 메인 페이지 컴포넌트

```tsx
// app/users/page.tsx

"use client";

import { useUsers } from "@/hooks/use-users";
import { SearchInput } from "@/components/users/search-input";
import { RoleFilter } from "@/components/users/role-filter";
import { UsersTable } from "@/components/users/users-table";
import { Pagination } from "@/components/users/pagination";

export default function UsersPage() {
  const {
    users,
    total,
    totalPages,
    page,
    pageSize,
    search,
    role,
    isLoading,
    error,
    setPage,
    setSearch,
    setRole,
  } = useUsers();

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">사용자 관리</h1>
        <p className="text-muted-foreground">
          등록된 사용자를 검색하고 관리합니다.
        </p>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row">
        <div className="flex-1">
          <SearchInput value={search} onChange={setSearch} />
        </div>
        <RoleFilter value={role} onChange={setRole} />
      </div>

      {error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <UsersTable users={users} isLoading={isLoading} />

      <Pagination
        page={page}
        totalPages={totalPages}
        total={total}
        pageSize={pageSize}
        onPageChange={setPage}
      />
    </div>
  );
}
```

## API Route (Next.js App Router)

```typescript
// app/api/users/route.ts

import { NextRequest, NextResponse } from "next/server";
import type { Role, User, UsersResponse } from "@/types/user";

// 데모용 목업 데이터 생성
function generateMockUsers(): User[] {
  const names = [
    "김민수", "이서연", "박지훈", "최유나", "정현우",
    "강소영", "조태현", "윤미래", "한승민", "임지은",
    "오동현", "배수지", "신재욱", "류하은", "문성호",
    "양지혜", "권도윤", "홍서진", "전민규", "송예린",
  ];
  const roles: Role[] = ["admin", "editor", "viewer"];

  return names.map((name, i) => ({
    id: `user-${String(i + 1).padStart(3, "0")}`,
    name,
    email: `${name.toLowerCase().replace(/\s/g, "")}@example.com`,
    role: roles[i % roles.length],
    createdAt: new Date(2024, 0, 1 + i * 15).toISOString(),
  }));
}

const MOCK_USERS = generateMockUsers();

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const page = Math.max(1, Number(searchParams.get("page")) || 1);
  const pageSize = Math.min(
    100,
    Math.max(1, Number(searchParams.get("pageSize")) || 10)
  );
  const search = searchParams.get("search")?.toLowerCase() ?? "";
  const role = searchParams.get("role") as Role | null;

  let filtered = MOCK_USERS;

  if (search) {
    filtered = filtered.filter(
      (user) =>
        user.name.toLowerCase().includes(search) ||
        user.email.toLowerCase().includes(search)
    );
  }

  if (role && role !== "all") {
    filtered = filtered.filter((user) => user.role === role);
  }

  const total = filtered.length;
  const totalPages = Math.ceil(total / pageSize);
  const start = (page - 1) * pageSize;
  const users = filtered.slice(start, start + pageSize);

  const response: UsersResponse = {
    users,
    total,
    page,
    pageSize,
    totalPages,
  };

  return NextResponse.json(response);
}
```

## 파일 구조

```
app/
  users/
    page.tsx              # 메인 페이지
  api/
    users/
      route.ts            # API 엔드포인트
components/
  users/
    search-input.tsx      # 검색 입력
    role-filter.tsx       # 역할 필터
    users-table.tsx       # 테이블 본체
    role-badge.tsx        # 역할 뱃지
    pagination.tsx        # 페이지네이션
hooks/
  use-users.ts            # 데이터 페칭 훅
  use-debounce.ts         # 디바운스 훅
types/
  user.ts                 # 타입 정의
```

## 주요 기능 요약

| 기능 | 설명 |
|------|------|
| 검색 | 이름/이메일 기준 검색, 300ms 디바운스 적용 |
| 역할 필터 | admin, editor, viewer 필터링 |
| 페이지네이션 | 서버사이드 페이지네이션, 7페이지 이상 시 ellipsis 처리 |
| 로딩 상태 | 스켈레톤 UI로 로딩 표시 |
| 에러 처리 | API 실패 시 에러 메시지 표시 |
| 빈 상태 | 검색 결과 없을 때 안내 메시지 |
| 반응형 | 모바일/데스크톱 대응 레이아웃 |

## 사용 방법

1. 위 파일들을 Next.js(App Router) 프로젝트에 배치합니다.
2. `/users` 경로로 접속하면 사용자 테이블 페이지를 확인할 수 있습니다.
3. 실제 프로젝트에서는 `app/api/users/route.ts`의 목업 데이터를 데이터베이스 연결로 교체합니다.
