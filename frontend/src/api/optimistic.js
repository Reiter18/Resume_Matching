export function optimistic(queryClient, key, update) {
  return {
    onMutate: async (vars) => {
      await queryClient.cancelQueries({ queryKey: key }) 
      const previous = queryClient.getQueryData(key)
      queryClient.setQueryData(key, (old) => update(old, vars))
      return { previous }
    },
    onError: (_error, _vars, context) => queryClient.setQueryData(key, context.previous),
  }
}
