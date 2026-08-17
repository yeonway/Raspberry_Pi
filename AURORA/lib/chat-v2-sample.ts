import type {
  ChatV2Character,
  ChatV2FeedItem,
  ChatV2Room,
} from "@/types/chat-v2";
import type { ProfileData } from "@/lib/profile-store";

export const sampleProfiles: ProfileData[] = [
  {
    id: "profile-yeonwoo",
    name: "연우",
    shortDescription: "남자용",
    detailedDescription: "평범한 대학생. 호기심 많고 친절한 성격.",
    imageUrl: "https://placehold.co/400x500/6d2df6/ffffff?text=연우",
    genderLabel: "남성",
    enabled: true,
    order: 1,
  },
  {
    id: "profile-minji",
    name: "민지",
    shortDescription: "여자용",
    detailedDescription: "조용하지만 단단한 성격의 회사원.",
    imageUrl: "https://placehold.co/400x500/e91e63/ffffff?text=민지",
    genderLabel: "여성",
    enabled: true,
    order: 2,
  },
  {
    id: "profile-hyunwoo",
    name: "현우",
    shortDescription: "남자용",
    detailedDescription: "운동을 좋아하는 쾌활한 고등학생.",
    imageUrl: "https://placehold.co/400x500/2196f3/ffffff?text=현우",
    genderLabel: "남성",
    enabled: true,
    order: 3,
  },
];

export const sampleCharacters: ChatV2Character[] = [
  {
    id: "char-sia",
    name: "시아",
    avatarUrl: "https://placehold.co/80x80/6d2df6/ffffff?text=시아",
    nameColor: "#c4b5fd",
  },
  {
    id: "char-oduck",
    name: "오덕훈",
    avatarUrl: "https://placehold.co/80x80/22c55e/ffffff?text=오",
    nameColor: "#86efac",
  },
];

export const sampleFeedItems: ChatV2FeedItem[] = [
  {
    type: "message",
    id: "msg-1",
    sender: "ai",
    characterId: "char-oduck",
    content:
      '**오덕훈이 헤드셋을 벗으며 {{user}}를 돌아본다.**\n"야, 드디어 왔냐? 이거 봐봐. 내가 만든 AI챗봇인데 지 혼자 얘기한다?"',
    providerLabel: "zeta",
    createdAt: "10:21",
  },
  {
    type: "message",
    id: "msg-2",
    sender: "ai",
    characterId: "char-sia",
    content:
      '**시아가 눈을 반짝이며 화면을 들여다본다.**\n"우와, 진짜 신기하다. 나도 만들어보고 싶어."',
    providerLabel: "zeta",
    createdAt: "10:22",
  },
  {
    type: "message",
    id: "msg-3",
    sender: "ai",
    characterId: "char-oduck",
    content:
      '**오덕훈이 으쓱하며 의자를 뒤로 젖힌다.**\n"당연하지. 내가 누구냐? 덕질 10년차 오덕훈이다."',
    createdAt: "10:22",
  },
  {
    type: "message",
    id: "msg-4",
    sender: "user",
    content: "혹시 나도 도와줄 수 있어? 나도 AI랑 대화하는 챗봇 만들어보고 싶은데.",
    createdAt: "10:23",
  },
  {
    type: "image",
    id: "img-1",
    imageUrl: "https://placehold.co/600x400/1a1a2e/ffffff?text=검은+고양이+상자",
    alt: "검은 고양이가 골판지 상자 안에 웅크리고 있는 모습",
    aspectRatio: 1.5,
    generationStatus: "done",
    createdAt: "10:25",
  },
  {
    type: "message",
    id: "msg-5",
    sender: "ai",
    characterId: "char-sia",
    content:
      '**시아가 상자 안의 검은 고양이를 조심스럽게 쓰다듬는다.**\n"얘 이름은 뭐라고 지을까? 눈이 정말 예쁘다."\n\n"{{user}}님, 우리 얘 키워도 될까요?"',
    providerLabel: "zeta",
    createdAt: "10:26",
  },
  {
    type: "message",
    id: "msg-6",
    sender: "user",
    content: "당연하지! 내가 책임지고 잘 키울게. 이름은... '달'이 어때? 눈이 달처럼 빛나서.",
    createdAt: "10:27",
  },
  {
    type: "message",
    id: "msg-7",
    sender: "ai",
    characterId: "char-sia",
    content:
      '**시아가 기쁘게 고개를 끄덕이며 달을 품에 안는다.**\n"달이라... 정말 잘 어울리는 이름이야."\n\n**한 달 후 — 시아의 방**\n**침대 위에서 눈을 뜨는 시아. 그녀의 품에는 사람 크기의 고양이 수인이 잠들어 있다.**',
    createdAt: "10:30",
  },
  {
    type: "image",
    id: "img-2",
    imageUrl: "https://placehold.co/500x700/2d1b69/ffffff?text=고양이+수인+침대",
    alt: "침대에서 눈을 뜬 고양이 수인의 모습",
    aspectRatio: 0.714,
    generationStatus: "done",
    createdAt: "10:32",
  },
  {
    type: "message",
    id: "msg-8",
    sender: "user",
    content: "이게 무슨 일이야?! 달이 사람이 됐어!",
    createdAt: "10:33",
  },
  {
    type: "message",
    id: "msg-9",
    sender: "ai",
    characterId: "char-sia",
    content:
      '**시아가 놀라서 눈을 크게 뜨며 달을 바라본다.**\n**그녀의 목소리가 떨린다.**\n"달...? 너 진짜 달이야?"\n\n**고양이 수인이 천천히 눈을 뜨고 하품을 한다.**\n"응... 시아 누나... 배고파..."',
    createdAt: "10:34",
  },
  {
    type: "message",
    id: "msg-10",
    sender: "user",
    content: "와... 진짜 말을 한다! 시아, 이거 대박이야!",
    createdAt: "10:34",
  },
  {
    type: "message",
    id: "msg-11",
    sender: "ai",
    characterId: "char-oduck",
    content:
      '**문밖에서 오덕훈의 목소리가 들린다.**\n"야! 무슨 일이야? 방에서 이상한 소리 났는데?"\n**문을 열고 들어온 오덕훈이 입을 딱 벌린다.**\n"...내가 아직 꿈꾸는 건가?"',
    createdAt: "10:35",
  },
  {
    type: "message",
    id: "msg-12",
    sender: "ai",
    characterId: "char-sia",
    content:
      '**시아가 오덕훈을 돌아보며 웃는다.**\n"꿈 아니야. 달이... 사람이 됐어."\n"오늘부터 {{user}}님하고 나하고 오빠까지, 넷이서 같이 살자."',
    providerLabel: "zeta",
    createdAt: "10:36",
  },
  {
    type: "message",
    id: "msg-13",
    sender: "user",
    content: "좋아! 넷이서 함께라면 뭐든 재밌을 거야!",
    createdAt: "10:37",
  },
  {
    type: "message",
    id: "msg-14",
    sender: "ai",
    characterId: "char-oduck",
    content:
      '**오덕훈이 한숨을 쉬며 어깨를 으쓱인다.**\n"하... 내 인생은 왜 이렇게 판타지 소설이 되어가는 거냐."\n**하지만 입가에는 미소가 번져 있다.**',
    createdAt: "10:38",
  },
  {
    type: "message",
    id: "msg-15",
    sender: "ai",
    characterId: "char-sia",
    content:
      '**다음 날 아침 — 캠퍼스 중앙광장**\n**시아가 {{user}}의 손을 잡고 캠퍼스를 가로지른다.**\n"주인님, 학교가 정말 예뻐요. 저도 여기서 공부하고 싶어요."',
    providerLabel: "zeta",
    createdAt: "10:45",
  },
  {
    type: "image",
    id: "img-3",
    imageUrl: "https://placehold.co/600x350/1e3a5f/ffffff?text=캠퍼스+중앙광장",
    alt: "캠퍼스 중앙광장을 걷는 시아와 {{user}}",
    aspectRatio: 1.714,
    generationStatus: "done",
    createdAt: "10:47",
  },
  {
    type: "sceneInfo",
    id: "scene-1",
    date: "4월 25일 금요일",
    time: "09:45 AM",
    location: "캠퍼스 중앙광장",
    createdAt: "10:48",
  },
];

export const sampleRoom: ChatV2Room = {
  id: "room-v2-demo",
  title: "시아 | 여우 수인과 오타쿠",
  modelName: "zeta",
  characters: sampleCharacters,
  feedItems: sampleFeedItems,
};
