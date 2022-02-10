// https://docs.slatejs.org/walkthroughs/01-installing-slate

// Import React dependencies.
import React, { useState } from 'react'
import { Component } from 'react/cjs/react.production.min'
// Import the Slate editor factory.
import { createEditor } from 'slate'

// Import the Slate components and React plugin.
import { Slate, Editable, withReact } from 'slate-react'

const App = () => {
  const [editor] = useState(() => withReact(createEditor()))
  // Add the initial value when setting up our state.
  const [value, setValue] = useState([
    {
      type: 'paragraph',
      children: [{ text: 'A line of text in a paragraph.' }],
    },
  ])

  return (
    <Slate
      editor={editor}
      value={value}
      onChange={newValue => setValue(newValue)}
    >
      <Editable
        // Define a new handler which prints the key that was pressed.
        onKeyDown={event => {
          console.log(event.key)
        }}
      />
    </Slate>
  )
}

export default App