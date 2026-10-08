import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { getPersonalPage } from "@/modules/personal/services/personalServices";
import type { PersonalListParams } from "@/modules/personal/services/personalServices";

export function usePersonal(params: PersonalListParams) {
  const query = useQuery({
    queryKey: ["personal", "page", params],
    queryFn: () => getPersonalPage(params),
    staleTime: 60_000,
    placeholderData: keepPreviousData,
  });
  return {
    ...query,
    list: query.data?.data ?? [],
    meta: query.data?.meta ?? { page: params.page, per_page: params.perPage ?? 9, total: 0, total_pages: 0 },
  };
}
