# Comment System Component

## 1. Architecture Overview

### 설계 의도

댓글 시스템은 CRUD + 트리 구조(대댓글)라는 비교적 명확한 도메인이지만, 낙관적 업데이트가 결합되면 상태 관리 복잡도가 급격히 높아진다. 이를 제어하기 위해 다음 구조를 선택했다:

```
features/
  comments/
    types.ts                    # Zod 스키마 + 타입 정의
    hooks/
      use-comments.ts           # TanStack Query 기반 CRUD + 낙관적 업데이트
      use-comment-form.ts       # 작성/수정 폼 로직
    components/
      comment-section.tsx       # 최상위 컨테이너 (ErrorBoundary + Suspense)
      comment-list.tsx          # 댓글 목록 렌더링
      comment-item.tsx          # 개별 댓글 (재귀적으로 대댓글 렌더링)
      comment-form.tsx          # 댓글 작성/수정 폼 UI
      comment-actions.tsx       # 수정/삭제/답글 액션 버튼
    lib/
      comment-api.ts            # API 호출 함수 (서버 통신 레이어)
      comment-tree.ts           # 플랫 배열 <-> 트리 변환 유틸리티
```

### 핵심 설계 결정

1. **플랫 데이터 + 클라이언트 트리 변환**: DB에서는 `parentId`를 가진 플랫 배열로 저장하고, 클라이언트에서 트리로 변환한다. 이렇게 하면 낙관적 업데이트 시 플랫 배열에 추가/수정/삭제만 하면 되고, 트리 변환은 `useMemo`로 파생시킨다.

2. **TanStack Query의 낙관적 업데이트**: `onMutate`에서 캐시를 직접 조작하고, 실패 시 `onError`에서 롤백한다. 이 패턴은 TanStack Query가 공식적으로 권장하는 방식이다.

3. **재귀 컴포넌트**: `CommentItem`이 자신의 `replies`를 다시 `CommentList`로 렌더링하는 재귀 구조를 사용한다. 깊이 제한(`maxDepth`)을 두어 무한 중첩을 방지한다.

4. **관심사 분리**: 폼 상태(`useCommentForm`), 서버 상태(`useComments`, `useCreateComment` 등), UI(`CommentItem`, `CommentForm`)가 완전히 분리되어 있어, 어느 한 쪽을 변경해도 나머지에 영향이 없다.

### 컴포넌트 관계도

```
CommentSection (ErrorBoundary + Suspense)
  |-- CommentForm (새 댓글 작성)
  |-- CommentList
        |-- CommentItem (댓글)
        |     |-- CommentActions (수정/삭제/답글 버튼)
        |     |-- CommentForm (수정 모드 / 답글 작성)
        |     |-- CommentList (대댓글, 재귀)
        |           |-- CommentItem ...
        |-- CommentItem ...
```

---

## 2. Code Implementation

### Types/Schemas

```ts
// features/comments/types.ts

import { z } from 'zod';

// ─── Zod Schemas ───────────────────────────────────────────

export const CommentSchema = z.object({
  id: z.string().uuid(),
  postId: z.string().uuid(),
  parentId: z.string().uuid().nullable(),
  authorId: z.string().uuid(),
  authorName: z.string().min(1),
  authorAvatarUrl: z.string().url().nullable(),
  content: z.string().min(1, '댓글 내용을 입력해주세요.').max(2000, '댓글은 2000자 이내로 작성해주세요.'),
  createdAt: z.coerce.date(),
  updatedAt: z.coerce.date(),
  isDeleted: z.boolean().default(false),
});

export const CommentListResponseSchema = z.object({
  comments: z.array(CommentSchema),
  nextCursor: z.string().nullable(),
  totalCount: z.number().int().nonnegative(),
});

export const CreateCommentInputSchema = z.object({
  postId: z.string().uuid(),
  parentId: z.string().uuid().nullable().optional(),
  content: z.string().min(1, '댓글 내용을 입력해주세요.').max(2000, '댓글은 2000자 이내로 작성해주세요.'),
});

export const UpdateCommentInputSchema = z.object({
  commentId: z.string().uuid(),
  content: z.string().min(1, '댓글 내용을 입력해주세요.').max(2000, '댓글은 2000자 이내로 작성해주세요.'),
});

export const DeleteCommentInputSchema = z.object({
  commentId: z.string().uuid(),
});

// ─── TypeScript Types ──────────────────────────────────────

export type Comment = z.infer<typeof CommentSchema>;
export type CommentListResponse = z.infer<typeof CommentListResponseSchema>;
export type CreateCommentInput = z.infer<typeof CreateCommentInputSchema>;
export type UpdateCommentInput = z.infer<typeof UpdateCommentInputSchema>;
export type DeleteCommentInput = z.infer<typeof DeleteCommentInputSchema>;

/** 트리 구조로 변환된 댓글 */
export interface CommentNode extends Comment {
  replies: CommentNode[];
  depth: number;
}

/** 댓글 폼 상태 */
export type CommentFormMode =
  | { type: 'create'; parentId?: string }
  | { type: 'edit'; commentId: string; initialContent: string };
```

### Utility: 트리 변환

```ts
// features/comments/lib/comment-tree.ts

import type { Comment, CommentNode } from '../types';

/**
 * 플랫 댓글 배열을 트리 구조로 변환한다.
 * 삭제된 댓글이 자식을 가지고 있으면 "삭제된 댓글입니다" 표시용으로 유지하고,
 * 자식이 없으면 완전히 제거한다.
 */
export function buildCommentTree(
  comments: Comment[],
  maxDepth: number = 3,
): CommentNode[] {
  const childrenMap = new Map<string | null, Comment[]>();

  for (const comment of comments) {
    const parentId = comment.parentId ?? null;
    const existing = childrenMap.get(parentId);
    if (existing) {
      existing.push(comment);
    } else {
      childrenMap.set(parentId, [comment]);
    }
  }

  function buildNodes(parentId: string | null, depth: number): CommentNode[] {
    const children = childrenMap.get(parentId) ?? [];

    return children
      .map((comment) => {
        const effectiveDepth = Math.min(depth, maxDepth);
        const replies =
          depth < maxDepth ? buildNodes(comment.id, depth + 1) : [];

        // 삭제된 댓글이 자식이 없으면 제거
        if (comment.isDeleted && replies.length === 0) {
          return null;
        }

        return {
          ...comment,
          replies,
          depth: effectiveDepth,
        };
      })
      .filter((node): node is CommentNode => node !== null)
      .sort(
        (a, b) =>
          new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime(),
      );
  }

  return buildNodes(null, 0);
}

/** 트리에서 특정 댓글의 총 답글 수를 계산한다. */
export function countReplies(node: CommentNode): number {
  return node.replies.reduce(
    (count, reply) => count + 1 + countReplies(reply),
    0,
  );
}
```

### API Layer

```ts
// features/comments/lib/comment-api.ts

import {
  CommentListResponseSchema,
  CommentSchema,
  type CreateCommentInput,
  type UpdateCommentInput,
  type DeleteCommentInput,
  type Comment,
  type CommentListResponse,
} from '../types';

const BASE_URL = '/api/comments';

async function handleResponse<T>(
  response: Response,
  schema: { parse: (data: unknown) => T },
): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(
      (error as { message?: string }).message ?? `HTTP ${response.status}`,
    );
  }
  const data: unknown = await response.json();
  return schema.parse(data);
}

export async function fetchComments(
  postId: string,
  cursor?: string,
): Promise<CommentListResponse> {
  const params = new URLSearchParams({ postId });
  if (cursor) params.set('cursor', cursor);

  const response = await fetch(`${BASE_URL}?${params.toString()}`);
  return handleResponse(response, CommentListResponseSchema);
}

export async function createComment(
  input: CreateCommentInput,
): Promise<Comment> {
  const response = await fetch(BASE_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  return handleResponse(response, CommentSchema);
}

export async function updateComment(
  input: UpdateCommentInput,
): Promise<Comment> {
  const response = await fetch(`${BASE_URL}/${input.commentId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: input.content }),
  });
  return handleResponse(response, CommentSchema);
}

export async function deleteComment(
  input: DeleteCommentInput,
): Promise<Comment> {
  const response = await fetch(`${BASE_URL}/${input.commentId}`, {
    method: 'DELETE',
  });
  return handleResponse(response, CommentSchema);
}
```

### Hooks

```ts
// features/comments/hooks/use-comments.ts

'use client';

import {
  useInfiniteQuery,
  useMutation,
  useQueryClient,
  type InfiniteData,
} from '@tanstack/react-query';
import { useCallback } from 'react';
import type {
  Comment,
  CommentListResponse,
  CreateCommentInput,
  UpdateCommentInput,
  DeleteCommentInput,
} from '../types';
import {
  fetchComments,
  createComment,
  updateComment,
  deleteComment,
} from '../lib/comment-api';

// ─── Query Keys ────────────────────────────────────────────

export const commentKeys = {
  all: ['comments'] as const,
  list: (postId: string) => [...commentKeys.all, 'list', postId] as const,
};

// ─── Query Options ─────────────────────────────────────────

export function commentsQueryOptions(postId: string) {
  return {
    queryKey: commentKeys.list(postId),
    queryFn: ({ pageParam }: { pageParam: string | undefined }) =>
      fetchComments(postId, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage: CommentListResponse) => lastPage.nextCursor,
  };
}

// ─── Hooks ─────────────────────────────────────────────────

export function useComments(postId: string) {
  return useInfiniteQuery(commentsQueryOptions(postId));
}

/**
 * 낙관적 업데이트를 적용한 댓글 생성 뮤테이션.
 *
 * 동작 순서:
 * 1. onMutate: 서버 응답 전에 캐시에 임시 댓글을 추가
 * 2. 서버 요청 발송
 * 3-a. 성공 시 onSettled: 캐시를 서버 데이터로 동기화
 * 3-b. 실패 시 onError: 이전 캐시 상태로 롤백
 */
export function useCreateComment(postId: string, currentUserId: string, currentUserName: string) {
  const queryClient = useQueryClient();
  const queryKey = commentKeys.list(postId);

  return useMutation({
    mutationFn: createComment,

    onMutate: async (input: CreateCommentInput) => {
      // 진행 중인 쿼리를 취소하여 낙관적 업데이트가 덮어쓰이지 않게 한다
      await queryClient.cancelQueries({ queryKey });

      // 현재 캐시 스냅샷 저장 (롤백용)
      const previousData =
        queryClient.getQueryData<InfiniteData<CommentListResponse>>(queryKey);

      // 낙관적으로 캐시에 새 댓글 추가
      const optimisticComment: Comment = {
        id: crypto.randomUUID(),
        postId: input.postId,
        parentId: input.parentId ?? null,
        authorId: currentUserId,
        authorName: currentUserName,
        authorAvatarUrl: null,
        content: input.content,
        createdAt: new Date(),
        updatedAt: new Date(),
        isDeleted: false,
      };

      queryClient.setQueryData<InfiniteData<CommentListResponse>>(
        queryKey,
        (old) => {
          if (!old) return old;
          return {
            ...old,
            pages: old.pages.map((page, index) =>
              index === 0
                ? {
                    ...page,
                    comments: [...page.comments, optimisticComment],
                    totalCount: page.totalCount + 1,
                  }
                : page,
            ),
          };
        },
      );

      return { previousData, optimisticId: optimisticComment.id };
    },

    onError: (_error, _input, context) => {
      // 실패 시 이전 캐시로 롤백
      if (context?.previousData) {
        queryClient.setQueryData(queryKey, context.previousData);
      }
    },

    onSettled: () => {
      // 성공/실패 관계없이 서버와 동기화
      queryClient.invalidateQueries({ queryKey });
    },
  });
}

export function useUpdateComment(postId: string) {
  const queryClient = useQueryClient();
  const queryKey = commentKeys.list(postId);

  return useMutation({
    mutationFn: updateComment,

    onMutate: async (input: UpdateCommentInput) => {
      await queryClient.cancelQueries({ queryKey });

      const previousData =
        queryClient.getQueryData<InfiniteData<CommentListResponse>>(queryKey);

      queryClient.setQueryData<InfiniteData<CommentListResponse>>(
        queryKey,
        (old) => {
          if (!old) return old;
          return {
            ...old,
            pages: old.pages.map((page) => ({
              ...page,
              comments: page.comments.map((comment) =>
                comment.id === input.commentId
                  ? { ...comment, content: input.content, updatedAt: new Date() }
                  : comment,
              ),
            })),
          };
        },
      );

      return { previousData };
    },

    onError: (_error, _input, context) => {
      if (context?.previousData) {
        queryClient.setQueryData(queryKey, context.previousData);
      }
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });
}

export function useDeleteComment(postId: string) {
  const queryClient = useQueryClient();
  const queryKey = commentKeys.list(postId);

  return useMutation({
    mutationFn: deleteComment,

    onMutate: async (input: DeleteCommentInput) => {
      await queryClient.cancelQueries({ queryKey });

      const previousData =
        queryClient.getQueryData<InfiniteData<CommentListResponse>>(queryKey);

      // 소프트 삭제: isDeleted를 true로 변경
      queryClient.setQueryData<InfiniteData<CommentListResponse>>(
        queryKey,
        (old) => {
          if (!old) return old;
          return {
            ...old,
            pages: old.pages.map((page) => ({
              ...page,
              comments: page.comments.map((comment) =>
                comment.id === input.commentId
                  ? { ...comment, isDeleted: true }
                  : comment,
              ),
            })),
          };
        },
      );

      return { previousData };
    },

    onError: (_error, _input, context) => {
      if (context?.previousData) {
        queryClient.setQueryData(queryKey, context.previousData);
      }
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });
}

/** 모든 페이지에서 댓글을 플랫 배열로 추출하는 셀렉터 */
export function selectAllComments(
  data: InfiniteData<CommentListResponse> | undefined,
): Comment[] {
  if (!data) return [];
  return data.pages.flatMap((page) => page.comments);
}
```

```ts
// features/comments/hooks/use-comment-form.ts

'use client';

import { useState, useCallback } from 'react';
import type { CommentFormMode } from '../types';

interface UseCommentFormReturn {
  /** 현재 편집 중인 폼 상태. null이면 폼이 닫혀 있음 */
  formState: CommentFormMode | null;
  /** 새 댓글 작성 폼 열기 */
  openCreateForm: (parentId?: string) => void;
  /** 수정 폼 열기 */
  openEditForm: (commentId: string, initialContent: string) => void;
  /** 폼 닫기 */
  closeForm: () => void;
}

export function useCommentForm(): UseCommentFormReturn {
  const [formState, setFormState] = useState<CommentFormMode | null>(null);

  const openCreateForm = useCallback((parentId?: string) => {
    setFormState({ type: 'create', parentId });
  }, []);

  const openEditForm = useCallback(
    (commentId: string, initialContent: string) => {
      setFormState({ type: 'edit', commentId, initialContent });
    },
    [],
  );

  const closeForm = useCallback(() => {
    setFormState(null);
  }, []);

  return { formState, openCreateForm, openEditForm, closeForm };
}
```

### Components

```tsx
// features/comments/components/comment-section.tsx

'use client';

import { Suspense } from 'react';
import { ErrorBoundary } from 'react-error-boundary';
import { Button } from '@/components/ui/button';
import { AlertCircle } from 'lucide-react';
import { CommentList } from './comment-list';
import { CommentForm } from './comment-form';
import { useCreateComment } from '../hooks/use-comments';

interface CommentSectionProps {
  postId: string;
  currentUserId: string;
  currentUserName: string;
}

function CommentSectionFallback({ error, resetErrorBoundary }: {
  error: Error;
  resetErrorBoundary: () => void;
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-lg border border-destructive/50 bg-destructive/5 p-6">
      <AlertCircle className="h-8 w-8 text-destructive" />
      <p className="text-sm text-destructive">
        댓글을 불러오는 중 오류가 발생했습니다.
      </p>
      <p className="text-xs text-muted-foreground">{error.message}</p>
      <Button variant="outline" size="sm" onClick={resetErrorBoundary}>
        다시 시도
      </Button>
    </div>
  );
}

function CommentSectionSkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="flex gap-3">
          <div className="h-8 w-8 animate-pulse rounded-full bg-muted" />
          <div className="flex-1 space-y-2">
            <div className="h-4 w-24 animate-pulse rounded bg-muted" />
            <div className="h-4 w-full animate-pulse rounded bg-muted" />
            <div className="h-4 w-2/3 animate-pulse rounded bg-muted" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function CommentSection({
  postId,
  currentUserId,
  currentUserName,
}: CommentSectionProps) {
  const createMutation = useCreateComment(postId, currentUserId, currentUserName);

  return (
    <section aria-label="댓글" className="space-y-6">
      <CommentForm
        mode={{ type: 'create' }}
        onSubmit={(content) => {
          createMutation.mutate({ postId, content });
        }}
        isPending={createMutation.isPending}
      />

      <ErrorBoundary FallbackComponent={CommentSectionFallback}>
        <Suspense fallback={<CommentSectionSkeleton />}>
          <CommentList
            postId={postId}
            currentUserId={currentUserId}
            currentUserName={currentUserName}
          />
        </Suspense>
      </ErrorBoundary>
    </section>
  );
}
```

```tsx
// features/comments/components/comment-list.tsx

'use client';

import { useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { useComments, selectAllComments } from '../hooks/use-comments';
import { buildCommentTree } from '../lib/comment-tree';
import { CommentItem } from './comment-item';

interface CommentListProps {
  postId: string;
  currentUserId: string;
  currentUserName: string;
  maxDepth?: number;
}

export function CommentList({
  postId,
  currentUserId,
  currentUserName,
  maxDepth = 3,
}: CommentListProps) {
  const {
    data,
    hasNextPage,
    fetchNextPage,
    isFetchingNextPage,
  } = useComments(postId);

  const flatComments = useMemo(() => selectAllComments(data), [data]);
  const commentTree = useMemo(
    () => buildCommentTree(flatComments, maxDepth),
    [flatComments, maxDepth],
  );

  const totalCount = data?.pages[0]?.totalCount ?? 0;

  if (commentTree.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        아직 댓글이 없습니다. 첫 댓글을 남겨보세요!
      </p>
    );
  }

  return (
    <div className="space-y-1">
      <p className="text-sm font-medium text-foreground">
        댓글 {totalCount}개
      </p>

      <div className="divide-y divide-border">
        {commentTree.map((node) => (
          <CommentItem
            key={node.id}
            node={node}
            postId={postId}
            currentUserId={currentUserId}
            currentUserName={currentUserName}
          />
        ))}
      </div>

      {hasNextPage && (
        <div className="flex justify-center pt-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => fetchNextPage()}
            disabled={isFetchingNextPage}
          >
            {isFetchingNextPage ? '불러오는 중...' : '댓글 더 보기'}
          </Button>
        </div>
      )}
    </div>
  );
}
```

```tsx
// features/comments/components/comment-item.tsx

'use client';

import { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { ko } from 'date-fns/locale';
import { cn } from '@/lib/utils';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import type { CommentNode } from '../types';
import {
  useCreateComment,
  useUpdateComment,
  useDeleteComment,
} from '../hooks/use-comments';
import { CommentActions } from './comment-actions';
import { CommentForm } from './comment-form';

interface CommentItemProps {
  node: CommentNode;
  postId: string;
  currentUserId: string;
  currentUserName: string;
}

export function CommentItem({
  node,
  postId,
  currentUserId,
  currentUserName,
}: CommentItemProps) {
  const [activeForm, setActiveForm] = useState<'reply' | 'edit' | null>(null);

  const createMutation = useCreateComment(postId, currentUserId, currentUserName);
  const updateMutation = useUpdateComment(postId);
  const deleteMutation = useDeleteComment(postId);

  const isAuthor = node.authorId === currentUserId;
  const timeAgo = formatDistanceToNow(new Date(node.createdAt), {
    addSuffix: true,
    locale: ko,
  });
  const isEdited =
    new Date(node.updatedAt).getTime() - new Date(node.createdAt).getTime() >
    1000;

  function handleReply(content: string) {
    createMutation.mutate(
      { postId, parentId: node.id, content },
      { onSuccess: () => setActiveForm(null) },
    );
  }

  function handleEdit(content: string) {
    updateMutation.mutate(
      { commentId: node.id, content },
      { onSuccess: () => setActiveForm(null) },
    );
  }

  function handleDelete() {
    deleteMutation.mutate({ commentId: node.id });
  }

  // 삭제된 댓글이지만 답글이 있어 구조 유지용으로 남아있는 경우
  if (node.isDeleted) {
    return (
      <div
        className={cn('py-4', node.depth > 0 && 'ml-8 border-l-2 border-muted pl-4')}
      >
        <p className="text-sm italic text-muted-foreground">
          삭제된 댓글입니다.
        </p>
        {node.replies.length > 0 && (
          <div className="mt-2">
            {node.replies.map((reply) => (
              <CommentItem
                key={reply.id}
                node={reply}
                postId={postId}
                currentUserId={currentUserId}
                currentUserName={currentUserName}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      className={cn(
        'py-4',
        node.depth > 0 && 'ml-8 border-l-2 border-muted pl-4',
      )}
    >
      {/* 댓글 헤더 */}
      <div className="flex items-center gap-2">
        <Avatar className="h-7 w-7">
          <AvatarImage src={node.authorAvatarUrl ?? undefined} alt={node.authorName} />
          <AvatarFallback className="text-xs">
            {node.authorName.slice(0, 2)}
          </AvatarFallback>
        </Avatar>
        <span className="text-sm font-medium text-foreground">
          {node.authorName}
        </span>
        <span className="text-xs text-muted-foreground">{timeAgo}</span>
        {isEdited && (
          <span className="text-xs text-muted-foreground">(수정됨)</span>
        )}
      </div>

      {/* 댓글 본문 또는 수정 폼 */}
      {activeForm === 'edit' ? (
        <div className="mt-2">
          <CommentForm
            mode={{ type: 'edit', commentId: node.id, initialContent: node.content }}
            onSubmit={handleEdit}
            onCancel={() => setActiveForm(null)}
            isPending={updateMutation.isPending}
          />
        </div>
      ) : (
        <p className="mt-1 whitespace-pre-wrap text-sm text-foreground">
          {node.content}
        </p>
      )}

      {/* 액션 버튼 */}
      {activeForm !== 'edit' && (
        <CommentActions
          isAuthor={isAuthor}
          isDeleting={deleteMutation.isPending}
          onReply={() => setActiveForm(activeForm === 'reply' ? null : 'reply')}
          onEdit={() => setActiveForm('edit')}
          onDelete={handleDelete}
        />
      )}

      {/* 답글 폼 */}
      {activeForm === 'reply' && (
        <div className="mt-3">
          <CommentForm
            mode={{ type: 'create', parentId: node.id }}
            onSubmit={handleReply}
            onCancel={() => setActiveForm(null)}
            isPending={createMutation.isPending}
            placeholder={`${node.authorName}님에게 답글 작성...`}
          />
        </div>
      )}

      {/* 대댓글 (재귀) */}
      {node.replies.length > 0 && (
        <div className="mt-2">
          {node.replies.map((reply) => (
            <CommentItem
              key={reply.id}
              node={reply}
              postId={postId}
              currentUserId={currentUserId}
              currentUserName={currentUserName}
            />
          ))}
        </div>
      )}
    </div>
  );
}
```

```tsx
// features/comments/components/comment-actions.tsx

'use client';

import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { MessageSquare, Pencil, Trash2 } from 'lucide-react';

interface CommentActionsProps {
  isAuthor: boolean;
  isDeleting: boolean;
  onReply: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

export function CommentActions({
  isAuthor,
  isDeleting,
  onReply,
  onEdit,
  onDelete,
}: CommentActionsProps) {
  return (
    <div className="mt-1 flex items-center gap-1">
      <Button
        variant="ghost"
        size="sm"
        className="h-7 gap-1 px-2 text-xs text-muted-foreground hover:text-foreground"
        onClick={onReply}
      >
        <MessageSquare className="h-3.5 w-3.5" />
        답글
      </Button>

      {isAuthor && (
        <>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 gap-1 px-2 text-xs text-muted-foreground hover:text-foreground"
            onClick={onEdit}
          >
            <Pencil className="h-3.5 w-3.5" />
            수정
          </Button>

          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 gap-1 px-2 text-xs text-muted-foreground hover:text-destructive"
                disabled={isDeleting}
              >
                <Trash2 className="h-3.5 w-3.5" />
                삭제
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>댓글을 삭제하시겠습니까?</AlertDialogTitle>
                <AlertDialogDescription>
                  삭제된 댓글은 복구할 수 없습니다. 답글이 있는 경우 &ldquo;삭제된
                  댓글입니다&rdquo;로 표시됩니다.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>취소</AlertDialogCancel>
                <AlertDialogAction
                  onClick={onDelete}
                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                >
                  삭제
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </>
      )}
    </div>
  );
}
```

```tsx
// features/comments/components/comment-form.tsx

'use client';

import { useRef, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Loader2 } from 'lucide-react';
import type { CommentFormMode } from '../types';

const formSchema = z.object({
  content: z
    .string()
    .min(1, '댓글 내용을 입력해주세요.')
    .max(2000, '댓글은 2000자 이내로 작성해주세요.'),
});

type FormValues = z.infer<typeof formSchema>;

interface CommentFormProps {
  mode: CommentFormMode;
  onSubmit: (content: string) => void;
  onCancel?: () => void;
  isPending?: boolean;
  placeholder?: string;
}

export function CommentForm({
  mode,
  onSubmit,
  onCancel,
  isPending = false,
  placeholder = '댓글을 작성해주세요...',
}: CommentFormProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isValid },
  } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      content: mode.type === 'edit' ? mode.initialContent : '',
    },
    mode: 'onChange',
  });

  const { ref: registerRef, ...registerRest } = register('content');

  // 수정/답글 폼이 열릴 때 자동 포커스
  useEffect(() => {
    if (mode.type === 'edit' || mode.type === 'create') {
      textareaRef.current?.focus();
    }
  }, [mode.type]);

  function onFormSubmit(values: FormValues) {
    onSubmit(values.content);
    if (mode.type === 'create') {
      reset({ content: '' });
    }
  }

  return (
    <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-2">
      <Textarea
        {...registerRest}
        ref={(el) => {
          registerRef(el);
          textareaRef.current = el;
        }}
        placeholder={placeholder}
        className="min-h-20 resize-none"
        aria-label={mode.type === 'edit' ? '댓글 수정' : '댓글 작성'}
        aria-invalid={!!errors.content}
      />

      {errors.content && (
        <p className="text-xs text-destructive" role="alert">
          {errors.content.message}
        </p>
      )}

      <div className="flex items-center justify-end gap-2">
        {onCancel && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onCancel}
            disabled={isPending}
          >
            취소
          </Button>
        )}
        <Button type="submit" size="sm" disabled={!isValid || isPending}>
          {isPending && <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />}
          {mode.type === 'edit' ? '수정' : '등록'}
        </Button>
      </div>
    </form>
  );
}
```

```ts
// features/comments/index.ts

export { CommentSection } from './components/comment-section';
export type { Comment, CommentNode, CreateCommentInput } from './types';
```

### Usage Example

```tsx
// app/posts/[postId]/page.tsx

import { CommentSection } from '@/features/comments';

interface PostPageProps {
  params: Promise<{ postId: string }>;
}

export default async function PostPage({ params }: PostPageProps) {
  const { postId } = await params;

  // 실제 프로젝트에서는 세션에서 가져옴
  const currentUserId = 'current-user-id';
  const currentUserName = '홍길동';

  return (
    <main className="mx-auto max-w-2xl px-4 py-8">
      {/* 게시글 내용 ... */}

      <div className="mt-12 border-t pt-8">
        <h2 className="mb-6 text-lg font-semibold">댓글</h2>
        <CommentSection
          postId={postId}
          currentUserId={currentUserId}
          currentUserName={currentUserName}
        />
      </div>
    </main>
  );
}
```

---

## 3. Review Points

### 특히 신경 쓴 부분

1. **낙관적 업데이트의 안정성**: 각 뮤테이션에서 `cancelQueries` -> 스냅샷 저장 -> 캐시 조작 -> 실패 시 롤백 -> 완료 시 무효화의 5단계를 빠짐없이 구현했다. 이 중 하나라도 빠지면 캐시 불일치가 발생할 수 있다. 특히 `cancelQueries`를 빠뜨리면 refetch 결과가 낙관적 업데이트를 덮어쓰는 레이스 컨디션이 발생한다.

2. **소프트 삭제 + 트리 구조 보전**: 댓글 삭제 시 답글이 있으면 "삭제된 댓글입니다"로 표시하고, 답글이 없으면 완전히 제거한다. 이 로직은 `buildCommentTree` 유틸리티에 집중되어 있어 변경이 용이하다.

3. **삭제 확인 다이얼로그**: `AlertDialog`(shadcn/ui)를 사용해 실수로 삭제하는 것을 방지했다. 삭제는 되돌릴 수 없으므로 UX적으로 중요하다.

4. **접근성**: `aria-label`, `aria-invalid`, `role="alert"` 등을 적용했다. shadcn/ui가 Radix UI 위에 구축되어 있으므로 다이얼로그의 포커스 트랩 등은 자동으로 처리된다.

### 요구사항 변경 시 수정 포인트

| 변경 사항 | 수정 위치 |
|---|---|
| 댓글에 좋아요/이모지 반응 추가 | `types.ts`에 필드 추가, `comment-item.tsx`에 UI 추가, 새로운 뮤테이션 훅 추가 |
| 댓글 정렬 순서 변경 (최신순/인기순) | `comment-tree.ts`의 `sort` 로직 변경 또는 서버 쿼리 파라미터 추가 |
| 대댓글 깊이 제한 변경 | `CommentList`의 `maxDepth` prop 조정 |
| 댓글 멘션(@사용자) 기능 | `comment-form.tsx`에 멘션 자동완성 UI 추가, `content` 파싱 로직 추가 |
| 실시간 업데이트 (WebSocket) | `use-comments.ts`에 WebSocket 구독 추가, `queryClient.setQueryData`로 실시간 반영 |
| 페이지네이션 -> 무한 스크롤 | 이미 `useInfiniteQuery`를 사용하고 있으므로 `IntersectionObserver` 트리거만 추가 |

### 잠재적 성능 이슈 및 확장 고려사항

1. **대규모 댓글 렌더링 성능**: 댓글이 수백 개 이상이면 재귀 트리 렌더링이 느려질 수 있다. 이 경우 `react-window` 또는 `@tanstack/react-virtual`로 가상 스크롤을 적용하되, 트리 구조 가상화는 별도의 flatten + offset 계산이 필요하다.

2. **`buildCommentTree`의 연산 비용**: `useMemo`로 캐싱하고 있지만, 댓글 수가 수천 개를 넘으면 페이지 단위로 트리를 분할하거나 서버에서 트리를 구성하여 내려보내는 것이 낫다.

3. **낙관적 업데이트 시 임시 ID 충돌**: `crypto.randomUUID()`는 충돌 확률이 극히 낮지만, `onSettled`에서 `invalidateQueries`로 서버 데이터와 동기화하므로 임시 ID는 곧 서버 ID로 교체된다.

4. **CommentItem의 뮤테이션 훅 호출**: 각 `CommentItem`에서 뮤테이션 훅을 호출하는데, TanStack Query의 `useMutation`은 구독을 생성하지 않으므로 리렌더 비용은 무시할 수 있다. 다만 수백 개의 댓글이 동시에 마운트되는 상황에서는 Context Provider를 통해 뮤테이션 함수를 공유하는 패턴을 고려할 수 있다.

5. **서버 컴포넌트 경계**: 현재 모든 댓글 컴포넌트가 클라이언트 컴포넌트다. 게시글 페이지 자체는 서버 컴포넌트로 유지하고, `CommentSection`만 클라이언트 경계로 분리하여 초기 페이지 로드 성능을 최적화했다. 서버에서 초기 댓글 데이터를 prefetch하여 `HydrationBoundary`로 전달하면 초기 로딩 UX를 더 개선할 수 있다.
