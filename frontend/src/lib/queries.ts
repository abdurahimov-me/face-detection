import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { deleteFaceUser, enrollFace, listFaceUsers } from './api'

export const faceUsersQueryKey = ['face-users'] as const

export function useFaceUsers() {
  return useQuery({
    queryKey: faceUsersQueryKey,
    queryFn: listFaceUsers,
    staleTime: 15_000,
  })
}

export function useEnrollFace() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: enrollFace,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: faceUsersQueryKey }),
  })
}

export function useDeleteFaceUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteFaceUser,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: faceUsersQueryKey }),
  })
}
