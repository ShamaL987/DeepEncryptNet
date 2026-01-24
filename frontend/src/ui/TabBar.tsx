type Props = {
    tabs: string[]
    active: string
    onChange: (tab: string) => void
}

const TabBar = ({ tabs, active, onChange }: Props) => {
    return (
        <div
            style={{
                display: 'flex',
                gap: 12,
                marginBottom: 24
            }}
        >
            {tabs.map(tab => (
                <button
                    key={tab}
                    onClick={() => onChange(tab)}
                    style={{
                        padding: '10px 18px',
                        borderRadius: 999,
                        border: 'none',
                        cursor: 'pointer',
                        background:
                            tab === active
                                ? 'rgba(255,255,255,0.15)'
                                : 'rgba(255,255,255,0.05)',
                        color: '#fff',
                        fontWeight: tab === active ? 600 : 400,
                        transition: 'all 0.2s ease'
                    }}
                >
                    {tab}
                </button>
            ))}
        </div>
    )
}

export default TabBar
