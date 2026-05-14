# 댓글 시스템 컴포넌트

댓글 작성, 수정, 삭제, 대댓글, 낙관적 업데이트를 지원하는 React 댓글 시스템입니다.

## 파일 구조

```
src/
  features/
    comments/
      types.ts
      hooks/
        useComments.ts
        useOptimisticComments.ts
      api/
        comments-api.ts
      components/
        CommentSystem.tsx
        CommentList.tsx
        CommentItem.tsx
        CommentForm.tsx
      utils/
        comment-tree.ts
```

---

## 1. 타입 정의 (`types.ts`)

```typescript
export interface Comment {
  id: string;
  parentId: string | null;
  content: string;
  author: {
    id: string;
    name: string;
    avatarUrl?: string;
  };
  createdAt: string;
  updatedAt: string;
  children: Comment[];
  isDeleted: boolean;
}

export interface CreateCommentPayload {
  content: string;
  parentId: string | null;
}

export interface UpdateCommentPayload {
  id: string;
  content: string;
}

export interface DeleteCommentPayload {
  id: string;
}

/** 낙관적 업데이트 상태 추적용 */
export type OptimisticStatus = "pending" | "confirmed" | "failed";

export interface OptimisticComment extends Comment {
  _optimistic?: {
    status: OptimisticStatus;
    tempId?: string;
    operation: "create" | "update" | "delete";
  };
}
```

---

## 2. 유틸리티 - 트리 변환 (`utils/comment-tree.ts`)

```typescript
import type { Comment } from "../types";

/**
 * 플랫 댓글 배열을 중첩 트리 구조로 변환한다.
 * parentId === null 인 댓글이 루트가 된다.
 */
export function buildCommentTree(flatComments: Omit<Comment, "children">[]): Comment[] {
  const map = new Map<string, Comment>();
  const roots: Comment[] = [];

  // 1단계: 모든 댓글을 children 빈 배열과 함께 맵에 등록
  for (const comment of flatComments) {
    map.set(comment.id, { ...comment, children: [] });
  }

  // 2단계: 부모-자식 관계 연결
  for (const comment of map.values()) {
    if (comment.parentId === null) {
      roots.push(comment);
    } else {
      const parent = map.get(comment.parentId);
      if (parent) {
        parent.children.push(comment);
      } else {
        // 부모가 없으면 루트로 처리
        roots.push(comment);
      }
    }
  }

  // 생성일 기준 오름차순 정렬 (재귀)
  const sortRecursive = (comments: Comment[]): Comment[] => {
    comments.sort(
      (a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
    );
    for (const c of comments) {
      sortRecursive(c.children);
    }
    return comments;
  };

  return sortRecursive(roots);
}

/**
 * 트리에서 특정 댓글을 찾는다.
 */
export function findCommentInTree(
  tree: Comment[],
  id: string
): Comment | null {
  for (const comment of tree) {
    if (comment.id === id) return comment;
    const found = findCommentInTree(comment.children, id);
    if (found) return found;
  }
  return null;
}
```

---

## 3. API 레이어 (`api/comments-api.ts`)

```typescript
import type {
  Comment,
  CreateCommentPayload,
  UpdateCommentPayload,
  DeleteCommentPayload,
} from "../types";

const API_BASE = "/api/comments";

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: "Unknown error" }));
    throw new Error(error.message ?? `HTTP ${response.status}`);
  }
  return response.json();
}

export const commentsApi = {
  /** 특정 게시글의 댓글 목록 조회 */
  async fetchComments(postId: string): Promise<Omit<Comment, "children">[]> {
    const res = await fetch(`${API_BASE}?postId=${postId}`);
    return handleResponse(res);
  },

  /** 댓글 생성 */
  async createComment(
    postId: string,
    payload: CreateCommentPayload
  ): Promise<Comment> {
    const res = await fetch(`${API_BASE}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ postId, ...payload }),
    });
    return handleResponse(res);
  },

  /** 댓글 수정 */
  async updateComment(payload: UpdateCommentPayload): Promise<Comment> {
    const res = await fetch(`${API_BASE}/${payload.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: payload.content }),
    });
    return handleResponse(res);
  },

  /** 댓글 삭제 */
  async deleteComment(payload: DeleteCommentPayload): Promise<void> {
    const res = await fetch(`${API_BASE}/${payload.id}`, {
      method: "DELETE",
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({ message: "Unknown error" }));
      throw new Error(error.message ?? `HTTP ${res.status}`);
    }
  },
};
```

---

## 4. 낙관적 업데이트 훅 (`hooks/useOptimisticComments.ts`)

```typescript
import { useCallback, useRef } from "react";
import type { Comment, OptimisticComment } from "../types";

interface OptimisticActions {
  /** 낙관적으로 댓글을 추가하고, 롤백 함수를 반환한다. */
  addOptimistic: (comment: OptimisticComment) => () => void;
  /** 낙관적으로 댓글을 수정하고, 롤백 함수를 반환한다. */
  updateOptimistic: (id: string, content: string) => () => void;
  /** 낙관적으로 댓글을 삭제하고, 롤백 함수를 반환한다. */
  deleteOptimistic: (id: string) => () => void;
  /** 임시 ID를 실제 ID로 교체한다. */
  confirmOptimistic: (tempId: string, realComment: Comment) => void;
}

/**
 * 댓글 목록에 대한 낙관적 업데이트 로직을 캡슐화한다.
 *
 * 핵심 패턴:
 * 1. 변경 전 스냅샷을 저장한다.
 * 2. UI를 즉시 업데이트한다.
 * 3. 실패 시 스냅샷으로 롤백한다.
 */
export function useOptimisticComments(
  comments: Comment[],
  setComments: React.Dispatch<React.SetStateAction<Comment[]>>
): OptimisticActions {
  const snapshotRef = useRef<Comment[]>([]);

  const takeSnapshot = useCallback(() => {
    snapshotRef.current = structuredClone(comments);
  }, [comments]);

  const rollback = useCallback(() => {
    setComments(snapshotRef.current);
  }, [setComments]);

  const addOptimistic = useCallback(
    (comment: OptimisticComment) => {
      takeSnapshot();
      setComments((prev) => {
        if (comment.parentId === null) {
          return [...prev, comment];
        }
        // 대댓글이면 부모를 찾아서 children에 추가
        return addChildComment(prev, comment.parentId, comment);
      });
      return rollback;
    },
    [takeSnapshot, setComments, rollback]
  );

  const updateOptimistic = useCallback(
    (id: string, content: string) => {
      takeSnapshot();
      setComments((prev) => updateCommentInTree(prev, id, content));
      return rollback;
    },
    [takeSnapshot, setComments, rollback]
  );

  const deleteOptimistic = useCallback(
    (id: string) => {
      takeSnapshot();
      setComments((prev) => softDeleteInTree(prev, id));
      return rollback;
    },
    [takeSnapshot, setComments, rollback]
  );

  const confirmOptimistic = useCallback(
    (tempId: string, realComment: Comment) => {
      setComments((prev) => replaceTempComment(prev, tempId, realComment));
    },
    [setComments]
  );

  return { addOptimistic, updateOptimistic, deleteOptimistic, confirmOptimistic };
}

// --- 트리 조작 헬퍼 ---

function addChildComment(
  tree: Comment[],
  parentId: string,
  child: Comment
): Comment[] {
  return tree.map((comment) => {
    if (comment.id === parentId) {
      return { ...comment, children: [...comment.children, child] };
    }
    if (comment.children.length > 0) {
      return {
        ...comment,
        children: addChildComment(comment.children, parentId, child),
      };
    }
    return comment;
  });
}

function updateCommentInTree(
  tree: Comment[],
  id: string,
  content: string
): Comment[] {
  return tree.map((comment) => {
    if (comment.id === id) {
      return {
        ...comment,
        content,
        updatedAt: new Date().toISOString(),
      };
    }
    if (comment.children.length > 0) {
      return {
        ...comment,
        children: updateCommentInTree(comment.children, id, content),
      };
    }
    return comment;
  });
}

function softDeleteInTree(tree: Comment[], id: string): Comment[] {
  return tree.map((comment) => {
    if (comment.id === id) {
      // 자식이 있으면 soft delete, 없으면 목록에서 제거
      if (comment.children.length > 0) {
        return {
          ...comment,
          content: "",
          isDeleted: true,
        };
      }
      return null as unknown as Comment; // 필터로 제거
    }
    if (comment.children.length > 0) {
      return {
        ...comment,
        children: softDeleteInTree(comment.children, id).filter(Boolean),
      };
    }
    return comment;
  }).filter(Boolean);
}

function replaceTempComment(
  tree: Comment[],
  tempId: string,
  real: Comment
): Comment[] {
  return tree.map((comment) => {
    if (comment.id === tempId) {
      return { ...real, children: comment.children };
    }
    if (comment.children.length > 0) {
      return {
        ...comment,
        children: replaceTempComment(comment.children, tempId, real),
      };
    }
    return comment;
  });
}
```

---

## 5. 댓글 비즈니스 로직 훅 (`hooks/useComments.ts`)

```typescript
import { useState, useCallback, useEffect } from "react";
import type { Comment, OptimisticComment } from "../types";
import { commentsApi } from "../api/comments-api";
import { buildCommentTree } from "../utils/comment-tree";
import { useOptimisticComments } from "./useOptimisticComments";

interface UseCommentsReturn {
  comments: Comment[];
  isLoading: boolean;
  error: string | null;
  createComment: (content: string, parentId?: string | null) => Promise<void>;
  updateComment: (id: string, content: string) => Promise<void>;
  deleteComment: (id: string) => Promise<void>;
}

export function useComments(
  postId: string,
  currentUser: { id: string; name: string; avatarUrl?: string }
): UseCommentsReturn {
  const [comments, setComments] = useState<Comment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const {
    addOptimistic,
    updateOptimistic,
    deleteOptimistic,
    confirmOptimistic,
  } = useOptimisticComments(comments, setComments);

  // 초기 데이터 로드
  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setIsLoading(true);
        setError(null);
        const flat = await commentsApi.fetchComments(postId);
        if (!cancelled) {
          setComments(buildCommentTree(flat));
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load comments");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [postId]);

  // 댓글 작성 (낙관적)
  const createComment = useCallback(
    async (content: string, parentId: string | null = null) => {
      const tempId = `temp-${crypto.randomUUID()}`;
      const now = new Date().toISOString();

      const optimisticComment: OptimisticComment = {
        id: tempId,
        parentId,
        content,
        author: currentUser,
        createdAt: now,
        updatedAt: now,
        children: [],
        isDeleted: false,
        _optimistic: { status: "pending", tempId, operation: "create" },
      };

      const rollback = addOptimistic(optimisticComment);

      try {
        const created = await commentsApi.createComment(postId, {
          content,
          parentId,
        });
        confirmOptimistic(tempId, created);
      } catch (err) {
        rollback();
        setError(err instanceof Error ? err.message : "Failed to create comment");
        throw err;
      }
    },
    [postId, currentUser, addOptimistic, confirmOptimistic]
  );

  // 댓글 수정 (낙관적)
  const updateComment = useCallback(
    async (id: string, content: string) => {
      const rollback = updateOptimistic(id, content);

      try {
        await commentsApi.updateComment({ id, content });
      } catch (err) {
        rollback();
        setError(err instanceof Error ? err.message : "Failed to update comment");
        throw err;
      }
    },
    [updateOptimistic]
  );

  // 댓글 삭제 (낙관적)
  const deleteComment = useCallback(
    async (id: string) => {
      const rollback = deleteOptimistic(id);

      try {
        await commentsApi.deleteComment({ id });
      } catch (err) {
        rollback();
        setError(err instanceof Error ? err.message : "Failed to delete comment");
        throw err;
      }
    },
    [deleteOptimistic]
  );

  return {
    comments,
    isLoading,
    error,
    createComment,
    updateComment,
    deleteComment,
  };
}
```

---

## 6. 댓글 작성 폼 (`components/CommentForm.tsx`)

```tsx
import { useState, useRef, useCallback } from "react";

interface CommentFormProps {
  onSubmit: (content: string) => Promise<void>;
  placeholder?: string;
  initialValue?: string;
  autoFocus?: boolean;
  onCancel?: () => void;
  submitLabel?: string;
}

export function CommentForm({
  onSubmit,
  placeholder = "댓글을 입력하세요...",
  initialValue = "",
  autoFocus = false,
  onCancel,
  submitLabel = "등록",
}: CommentFormProps) {
  const [content, setContent] = useState(initialValue);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const trimmed = content.trim();
      if (!trimmed || isSubmitting) return;

      setIsSubmitting(true);
      try {
        await onSubmit(trimmed);
        setContent("");
        // 높이 초기화
        if (textareaRef.current) {
          textareaRef.current.style.height = "auto";
        }
      } catch {
        // 에러는 상위에서 처리 - 입력값 유지
      } finally {
        setIsSubmitting(false);
      }
    },
    [content, isSubmitting, onSubmit]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        const form = e.currentTarget.closest("form");
        form?.requestSubmit();
      }
      if (e.key === "Escape" && onCancel) {
        onCancel();
      }
    },
    [onCancel]
  );

  // textarea 자동 높이 조절
  const handleInput = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setContent(e.target.value);
      const el = e.target;
      el.style.height = "auto";
      el.style.height = `${el.scrollHeight}px`;
    },
    []
  );

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2">
      <textarea
        ref={textareaRef}
        value={content}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        autoFocus={autoFocus}
        rows={3}
        disabled={isSubmitting}
        className="w-full resize-none rounded-lg border border-gray-300 px-3 py-2
                   text-sm leading-relaxed placeholder:text-gray-400
                   focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500
                   disabled:bg-gray-50 disabled:text-gray-400"
      />
      <div className="flex items-center justify-end gap-2">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            className="rounded-md px-3 py-1.5 text-sm text-gray-600
                       hover:bg-gray-100 disabled:opacity-50"
          >
            취소
          </button>
        )}
        <button
          type="submit"
          disabled={!content.trim() || isSubmitting}
          className="rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white
                     hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed
                     transition-colors"
        >
          {isSubmitting ? "등록 중..." : submitLabel}
        </button>
      </div>
      <p className="text-xs text-gray-400">Ctrl+Enter로 빠르게 등록</p>
    </form>
  );
}
```

---

## 7. 댓글 아이템 (`components/CommentItem.tsx`)

```tsx
import { useState, useCallback } from "react";
import type { Comment, OptimisticComment } from "../types";
import { CommentForm } from "./CommentForm";

interface CommentItemProps {
  comment: Comment;
  currentUserId: string;
  depth: number;
  onReply: (content: string, parentId: string) => Promise<void>;
  onUpdate: (id: string, content: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  maxDepth?: number;
}

const MAX_VISIBLE_DEPTH = 4;

export function CommentItem({
  comment,
  currentUserId,
  depth,
  onReply,
  onUpdate,
  onDelete,
  maxDepth = MAX_VISIBLE_DEPTH,
}: CommentItemProps) {
  const [isReplying, setIsReplying] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const isOwner = comment.author.id === currentUserId;
  const isOptimistic = !!(comment as OptimisticComment)._optimistic;
  const isPending =
    (comment as OptimisticComment)._optimistic?.status === "pending";

  const handleReply = useCallback(
    async (content: string) => {
      await onReply(content, comment.id);
      setIsReplying(false);
    },
    [comment.id, onReply]
  );

  const handleUpdate = useCallback(
    async (content: string) => {
      await onUpdate(comment.id, content);
      setIsEditing(false);
    },
    [comment.id, onUpdate]
  );

  const handleDelete = useCallback(async () => {
    await onDelete(comment.id);
    setShowDeleteConfirm(false);
  }, [comment.id, onDelete]);

  // 삭제된 댓글 표시
  if (comment.isDeleted) {
    return (
      <div className={`${depth > 0 ? "ml-8 border-l-2 border-gray-200 pl-4" : ""}`}>
        <p className="py-3 text-sm italic text-gray-400">
          삭제된 댓글입니다.
        </p>
        {comment.children.length > 0 && (
          <div className="mt-2 space-y-3">
            {comment.children.map((child) => (
              <CommentItem
                key={child.id}
                comment={child}
                currentUserId={currentUserId}
                depth={depth + 1}
                onReply={onReply}
                onUpdate={onUpdate}
                onDelete={onDelete}
                maxDepth={maxDepth}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  const timeAgo = formatRelativeTime(comment.createdAt);
  const isEdited = comment.createdAt !== comment.updatedAt;

  return (
    <div
      className={`group ${depth > 0 ? "ml-8 border-l-2 border-gray-200 pl-4" : ""}
                  ${isPending ? "opacity-60" : ""}`}
    >
      {/* 헤더 */}
      <div className="flex items-center gap-2">
        {comment.author.avatarUrl ? (
          <img
            src={comment.author.avatarUrl}
            alt={comment.author.name}
            className="h-7 w-7 rounded-full object-cover"
          />
        ) : (
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gray-200 text-xs font-medium text-gray-600">
            {comment.author.name.charAt(0).toUpperCase()}
          </div>
        )}
        <span className="text-sm font-medium text-gray-900">
          {comment.author.name}
        </span>
        <span className="text-xs text-gray-400">{timeAgo}</span>
        {isEdited && (
          <span className="text-xs text-gray-400">(수정됨)</span>
        )}
        {isPending && (
          <span className="text-xs text-blue-400">전송 중...</span>
        )}
      </div>

      {/* 본문 */}
      {isEditing ? (
        <div className="mt-2">
          <CommentForm
            onSubmit={handleUpdate}
            initialValue={comment.content}
            autoFocus
            onCancel={() => setIsEditing(false)}
            submitLabel="수정"
          />
        </div>
      ) : (
        <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-gray-700">
          {comment.content}
        </p>
      )}

      {/* 액션 버튼 */}
      {!isEditing && !isPending && (
        <div className="mt-1.5 flex items-center gap-3">
          {depth < maxDepth && (
            <button
              onClick={() => setIsReplying((prev) => !prev)}
              className="text-xs text-gray-500 hover:text-blue-600 transition-colors"
            >
              답글
            </button>
          )}
          {isOwner && (
            <>
              <button
                onClick={() => setIsEditing(true)}
                className="text-xs text-gray-500 hover:text-blue-600 transition-colors"
              >
                수정
              </button>
              {showDeleteConfirm ? (
                <span className="flex items-center gap-1.5 text-xs">
                  <span className="text-red-500">정말 삭제하시겠습니까?</span>
                  <button
                    onClick={handleDelete}
                    className="font-medium text-red-600 hover:text-red-700"
                  >
                    확인
                  </button>
                  <button
                    onClick={() => setShowDeleteConfirm(false)}
                    className="text-gray-500 hover:text-gray-700"
                  >
                    취소
                  </button>
                </span>
              ) : (
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  className="text-xs text-gray-500 hover:text-red-600 transition-colors"
                >
                  삭제
                </button>
              )}
            </>
          )}
        </div>
      )}

      {/* 답글 폼 */}
      {isReplying && (
        <div className="mt-3">
          <CommentForm
            onSubmit={handleReply}
            placeholder={`${comment.author.name}님에게 답글 작성...`}
            autoFocus
            onCancel={() => setIsReplying(false)}
            submitLabel="답글"
          />
        </div>
      )}

      {/* 자식 댓글 (재귀) */}
      {comment.children.length > 0 && (
        <div className="mt-3 space-y-3">
          {comment.children.map((child) => (
            <CommentItem
              key={child.id}
              comment={child}
              currentUserId={currentUserId}
              depth={depth + 1}
              onReply={onReply}
              onUpdate={onUpdate}
              onDelete={onDelete}
              maxDepth={maxDepth}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// --- 시간 포맷 헬퍼 ---

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffSeconds = Math.floor((now - then) / 1000);

  if (diffSeconds < 60) return "방금 전";
  if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}분 전`;
  if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)}시간 전`;
  if (diffSeconds < 2592000) return `${Math.floor(diffSeconds / 86400)}일 전`;

  return new Date(dateStr).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}
```

---

## 8. 댓글 목록 (`components/CommentList.tsx`)

```tsx
import type { Comment } from "../types";
import { CommentItem } from "./CommentItem";

interface CommentListProps {
  comments: Comment[];
  currentUserId: string;
  onReply: (content: string, parentId: string) => Promise<void>;
  onUpdate: (id: string, content: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}

export function CommentList({
  comments,
  currentUserId,
  onReply,
  onUpdate,
  onDelete,
}: CommentListProps) {
  if (comments.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-gray-400">
        아직 댓글이 없습니다. 첫 번째 댓글을 남겨보세요.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {comments.map((comment) => (
        <CommentItem
          key={comment.id}
          comment={comment}
          currentUserId={currentUserId}
          depth={0}
          onReply={onReply}
          onUpdate={onUpdate}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
}
```

---

## 9. 최상위 컴포넌트 (`components/CommentSystem.tsx`)

```tsx
import { useCallback } from "react";
import { useComments } from "../hooks/useComments";
import { CommentForm } from "./CommentForm";
import { CommentList } from "./CommentList";

interface CommentSystemProps {
  postId: string;
  currentUser: {
    id: string;
    name: string;
    avatarUrl?: string;
  };
}

export function CommentSystem({ postId, currentUser }: CommentSystemProps) {
  const {
    comments,
    isLoading,
    error,
    createComment,
    updateComment,
    deleteComment,
  } = useComments(postId, currentUser);

  const handleCreate = useCallback(
    async (content: string) => {
      await createComment(content, null);
    },
    [createComment]
  );

  const handleReply = useCallback(
    async (content: string, parentId: string) => {
      await createComment(content, parentId);
    },
    [createComment]
  );

  return (
    <section className="mx-auto w-full max-w-2xl" aria-label="댓글">
      <h2 className="mb-4 text-lg font-semibold text-gray-900">댓글</h2>

      {/* 새 댓글 작성 폼 */}
      <div className="mb-6">
        <CommentForm onSubmit={handleCreate} placeholder="댓글을 남겨보세요..." />
      </div>

      {/* 에러 표시 */}
      {error && (
        <div
          role="alert"
          className="mb-4 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {error}
        </div>
      )}

      {/* 로딩 */}
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
          <span className="ml-2 text-sm text-gray-500">댓글을 불러오는 중...</span>
        </div>
      ) : (
        <CommentList
          comments={comments}
          currentUserId={currentUser.id}
          onReply={handleReply}
          onUpdate={updateComment}
          onDelete={deleteComment}
        />
      )}
    </section>
  );
}
```

---

## 사용 예시

```tsx
import { CommentSystem } from "@/features/comments/components/CommentSystem";

export default function PostPage({ params }: { params: { id: string } }) {
  const currentUser = {
    id: "user-1",
    name: "홍길동",
    avatarUrl: "/avatars/hong.jpg",
  };

  return (
    <main className="p-6">
      <article>{/* 게시글 본문 */}</article>

      <hr className="my-8" />

      <CommentSystem postId={params.id} currentUser={currentUser} />
    </main>
  );
}
```

---

## 설계 결정 요약

| 항목 | 결정 | 이유 |
|---|---|---|
| **트리 구조** | 서버에서 플랫 배열 수신, 클라이언트에서 트리 변환 | API 유연성 확보, 정렬/필터 자유도 |
| **낙관적 업데이트** | 스냅샷 기반 롤백 패턴 | 실패 시 이전 상태 복원이 확실함 |
| **삭제 전략** | 자식이 있으면 soft delete, 없으면 물리 삭제 | 대댓글 컨텍스트 보존 |
| **대댓글 깊이** | 최대 4단계 (설정 가능) | 과도한 들여쓰기 방지 |
| **상태 관리** | `useState` + 커스텀 훅 | 외부 라이브러리 의존 없이 구현, 필요 시 Zustand/TanStack Query로 교체 용이 |
| **임시 ID** | `crypto.randomUUID()` 사용 | 서버 응답 전 클라이언트 식별자 필요 |
| **키보드 접근성** | Ctrl+Enter 등록, Escape 취소 | UX 편의성 |
