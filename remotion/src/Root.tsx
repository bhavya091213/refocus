import React from 'react';
import {Composition, Series} from 'remotion';
import {FocalStack, FOCAL_DUR} from './FocalStack';
import {DataPrep, DATA_DUR} from './DataPrep';
import {Conditioning, COND_DUR} from './Conditioning';
import {Inference, INF_DUR} from './Inference';
import {Results, RES_DUR} from './Results';
import {Outro, OUTRO_DUR} from './Outro';

const common = {width: 1280, height: 720, fps: 30};
const SCENES = [
  ['FocalStack', FocalStack, FOCAL_DUR], ['DataPrep', DataPrep, DATA_DUR], ['Conditioning', Conditioning, COND_DUR],
  ['Inference', Inference, INF_DUR], ['Results', Results, RES_DUR], ['Outro', Outro, OUTRO_DUR],
] as const;

const All: React.FC = () => (
  <Series>
    {SCENES.map(([n, Comp, d]) => (
      <Series.Sequence key={n} durationInFrames={d}><Comp /></Series.Sequence>
    ))}
  </Series>
);

export const Root: React.FC = () => (
  <>
    {SCENES.map(([n, Comp, d]) => <Composition key={n} id={n} component={Comp} durationInFrames={d} {...common} />)}
    <Composition id="All" component={All} durationInFrames={SCENES.reduce((s, x) => s + x[2], 0)} {...common} />
  </>
);
