"use client";

const GENRES = [
    {
        id: "tu_tien",
        emoji: "⚔️",
        label: "Tu Tiên / Huyền Huyễn",
        desc: "Văn phong cổ điển, thuật ngữ tu luyện",
    },
    {
        id: "dam_my",
        emoji: "💜",
        label: "Đam Mỹ (BL)",
        desc: "Tình cảm anh/em, lãng mạn",
    },
    {
        id: "romance",
        emoji: "💕",
        label: "Romance",
        desc: "Shoujo, manhwa, tình cảm hiện đại",
    },
    {
        id: "hentai",
        emoji: "🔞",
        label: "18+",
        desc: "Dịch đầy đủ, không kiểm duyệt",
    },
];

interface GenrePickerProps {
    selected: string;
    onSelect: (genre: string) => void;
}

export default function GenrePicker({ selected, onSelect }: GenrePickerProps) {
    return (
        <div className="genre-grid">
            {GENRES.map((g) => (
                <div
                    key={g.id}
                    className={`genre-card ${selected === g.id ? "selected" : ""}`}
                    onClick={() => onSelect(g.id)}
                >
                    <span className="emoji">{g.emoji}</span>
                    <div className="label">{g.label}</div>
                    <div className="desc">{g.desc}</div>
                </div>
            ))}
        </div>
    );
}
