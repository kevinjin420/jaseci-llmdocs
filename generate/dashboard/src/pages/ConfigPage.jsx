import SourcePanel from '../components/SourcePanel'
import FileEditor from '../components/FileEditor'

export default function ConfigPage({ sources, onAdd, onDelete, onToggle, onRefresh, onEdit }) {
  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 120px)' }}>
      <SourcePanel
        sources={sources}
        onAdd={onAdd}
        onDelete={onDelete}
        onToggle={onToggle}
        onRefresh={onRefresh}
        onEdit={onEdit}
      />
      <FileEditor />
    </div>
  )
}
