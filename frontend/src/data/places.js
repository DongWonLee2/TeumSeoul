export const CATEGORIES = [
  { key: 'attraction', label: '관광지', hue: 30, source: '관광지 정보 API' },
  { key: 'culture', label: '문화시설', hue: 285, source: '문화시설 정보 API' },
  { key: 'festival', label: '축제공연행사', hue: 340, source: '축제공연행사 정보 API' },
  { key: 'sports', label: '레포츠', hue: 145, source: '레포츠 정보 API' },
  { key: 'stay', label: '숙박', hue: 230, source: '숙박업소 정보 API' },
  { key: 'shopping', label: '쇼핑', hue: 190, source: '쇼핑정보 API' },
  { key: 'course', label: '여행코스', hue: 60, source: '여행코스 정보 API' },
]

export const SEOUL_DISTRICTS = [
  '종로구', '중구', '용산구', '성동구', '광진구', '동대문구', '중랑구',
  '성북구', '강북구', '도봉구', '노원구', '은평구', '서대문구', '마포구',
  '양천구', '강서구', '구로구', '금천구', '영등포구', '동작구', '관악구',
  '서초구', '강남구', '송파구', '강동구',
]

// 백엔드 연결 전 UI 확인용 데이터입니다. 필드명은 API 응답에 맞췄습니다.
export const PLACES = [
  { id: 1, title: '경복궁', content_type_id: 12, category: 'attraction', content_type: '관광지', district: '종로구', address: '서울 종로구 사직로 161', telephone: '02-3700-3900', latitude: 37.579617, longitude: 126.977041, image_url: null, source_modified_at: '2026-07-12', rating: 4.7, related_post_count: 1 },
  { id: 2, title: '국립중앙박물관', content_type_id: 14, category: 'culture', content_type: '문화시설', district: '용산구', address: '서울 용산구 서빙고로 137', telephone: '02-2077-9000', latitude: 37.523851, longitude: 126.98047, image_url: null, source_modified_at: '2026-07-10', rating: 4.8, related_post_count: 1 },
  { id: 3, title: '서울세계불꽃축제', content_type_id: 15, category: 'festival', content_type: '축제공연행사', district: '영등포구', address: '서울 영등포구 여의동로 330', telephone: '02-3780-0561', latitude: 37.528421, longitude: 126.934565, image_url: null, source_modified_at: '2026-07-14', rating: 4.6, related_post_count: 1 },
  { id: 4, title: '잠실 클라이밍파크', content_type_id: 28, category: 'sports', content_type: '레포츠', district: '송파구', address: '서울 송파구 올림픽로 25', telephone: '02-2140-7702', latitude: 37.512151, longitude: 127.071975, image_url: null, source_modified_at: '2026-07-13', rating: 4.5, related_post_count: 1 },
  { id: 5, title: '호텔신라 서울', content_type_id: 32, category: 'stay', content_type: '숙박', district: '중구', address: '서울 중구 동호로 249', telephone: '02-2233-3131', latitude: 37.556454, longitude: 127.005712, image_url: null, source_modified_at: '2026-07-08', rating: 4.6, related_post_count: 0 },
  { id: 6, title: '명동 쇼핑거리', content_type_id: 38, category: 'shopping', content_type: '쇼핑', district: '중구', address: '서울 중구 명동길 일대', telephone: '02-3396-7702', latitude: 37.56358, longitude: 126.98517, image_url: null, source_modified_at: '2026-07-14', rating: 4.3, related_post_count: 1 },
  { id: 7, title: '경복궁·북촌·인사동 도보코스', content_type_id: 25, category: 'course', content_type: '여행코스', district: '종로구', address: '경복궁역 5번 출구 ~ 인사동', telephone: '02-2148-4160', latitude: 37.58059, longitude: 126.984907, image_url: null, source_modified_at: '2026-07-11', rating: 4.7, related_post_count: 0 },
  { id: 8, title: '남산서울타워', content_type_id: 12, category: 'attraction', content_type: '관광지', district: '용산구', address: '서울 용산구 남산공원길 105', telephone: '02-3455-9277', latitude: 37.551169, longitude: 126.988227, image_url: null, source_modified_at: '2026-07-09', rating: 4.6, related_post_count: 1 },
]
